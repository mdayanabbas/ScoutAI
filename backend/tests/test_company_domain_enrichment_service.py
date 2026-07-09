from dataclasses import dataclass

import pytest

from app.enrichment.domain_validator import DomainValidationResult
from app.enrichment.ashby_public_job_parser import AshbyPublicJob
from app.enrichment.resolvers import (
    AshbyCompanyResolutionResult,
    AshbyJobBoardResult,
    YCCompanyResolutionResult,
)
from app.models.company import Company
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_run import DiscoveryRun
from app.services.company_domain_enrichment_service import (
    CompanyDomainEnrichmentService,
)
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
)


@dataclass
class FakeValidator:
    valid: bool = True
    reason: str | None = None

    async def validate(self, value: str):
        domain = (
            "getdexter.co"
            if "getdexter" in value
            else "infracost.io"
            if "infracost" in value
            else "supabase.com"
            if "supabase" in value
            else "acme.ai"
        )
        return DomainValidationResult(
            valid=self.valid,
            requested_url=value,
            final_url=f"https://{domain}",
            normalized_domain=domain if self.valid else None,
            status_code=200 if self.valid else None,
            reason=self.reason,
        )


class FakeYCResolver:
    def __init__(self, result: YCCompanyResolutionResult):
        self.result = result
        self.calls = 0

    def supports(self, candidate):
        return self.extract_company_slug(candidate) is not None

    def extract_company_slug(self, candidate):
        classification = (candidate.raw_payload or {}).get("url_classification") or {}
        if classification.get("platform") != "ycombinator":
            return None
        return classification.get("external_company_slug")

    async def resolve(self, candidate):
        self.calls += 1
        return self.result


class FakeAshbyResolver:
    def __init__(self, resolved: bool = True):
        self.resolved = resolved
        self.fetch_calls = 0
        self.job = AshbyPublicJob(
            title="Software Engineer",
            location="Remote",
            secondary_locations=(),
            department="Engineering",
            team="Database",
            is_listed=True,
            is_remote=True,
            workplace_type="Remote",
            description_plain="Apply via careers@supabase.com",
            description_html=None,
            published_at=None,
            employment_type="FullTime",
            job_url=(
                "https://jobs.ashbyhq.com/supabase/"
                "2e718684-4f75-4a99-8d6b-3b6bd44e4228"
            ),
            apply_url=None,
            compensation_summary="$150k-$200k",
            raw_posting_id="2e718684-4f75-4a99-8d6b-3b6bd44e4228",
        )

    def supports(self, candidate):
        classification = (candidate.raw_payload or {}).get("url_classification") or {}
        return classification.get("platform") == "ashby"

    def extract_board_slug(self, candidate):
        return ((candidate.raw_payload or {}).get("url_classification") or {}).get(
            "external_company_slug"
        )

    async def fetch_job_board(self, slug):
        self.fetch_calls += 1
        return AshbyJobBoardResult(True, slug, 200, (self.job,))

    async def resolve(self, candidate, board_result=None):
        if not self.resolved:
            return AshbyCompanyResolutionResult(
                False,
                board_slug="supabase",
                matched_job=self.job,
                status_code=200,
                reason="ashby_company_domain_missing",
                evidence={"listed_job_count": 1},
            )
        return AshbyCompanyResolutionResult(
            True,
            board_slug="supabase",
            posting_id=self.job.raw_posting_id,
            matched_job=self.job,
            proposed_website_url="supabase.com",
            proposed_domain="supabase.com",
            status_code=200,
            confidence=1.0,
            reason="ashby_company_domain_evidence",
            evidence={"listed_job_count": 1},
        )


def _yc_resolution(
    resolved: bool = True,
    reason: str | None = "clearly labelled profile website link",
):
    return YCCompanyResolutionResult(
        resolved=resolved,
        company_slug="infracost",
        profile_url="https://www.ycombinator.com/companies/infracost",
        proposed_website_url="https://www.infracost.io",
        proposed_domain="infracost.io",
        company_name="Infracost",
        description="Cloud cost tooling",
        evidence={"selected_source": "profile_website_link"},
        reason=reason,
        status_code=200 if resolved else 404,
        confidence=0.95 if resolved else None,
    )


def _deferred_candidate(
    db_session,
    text: str = "Apply at jobs@getdexter.co",
    raw_payload: dict | None = None,
    source_identifier: str = "hn:1",
    name: str = "Dexter",
):
    run = DiscoveryRun(
        source=DiscoverySource.HACKER_NEWS,
        status=DiscoveryRunStatus.SUCCESS,
        candidates_found=1,
        candidates_normalized=1,
        companies_created=0,
        companies_matched=0,
        candidates_deferred=1,
        candidates_rejected=0,
        candidates_failed=0,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    candidate = DiscoveryCandidate(
        discovery_run_id=run.id,
        source=DiscoverySource.HACKER_NEWS,
        source_identifier=source_identifier,
        raw_name=name,
        raw_description=text,
        normalized_name=name,
        normalized_description=text,
        status=DiscoveryCandidateStatus.NORMALIZED,
        decision=DiscoveryDecision.DEFERRED,
        deferred_reason="requires_company_domain_enrichment",
        raw_payload=raw_payload or {"text": text},
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def _yc_candidate(db_session, source_identifier: str = "hn:yc"):
    return _deferred_candidate(
        db_session,
        text="Apply through YC",
        raw_payload={
            "url": "https://www.ycombinator.com/companies/infracost/jobs/engineer",
            "url_classification": {
                "platform": "ycombinator",
                "external_company_slug": "infracost",
                "url_type": "yc_job",
                "original_url": "https://www.ycombinator.com/companies/infracost/jobs/engineer",
            },
        },
        source_identifier=source_identifier,
        name="Infracost",
    )


def _ashby_candidate(db_session, source_identifier: str = "hn:ashby"):
    url = (
        "https://jobs.ashbyhq.com/supabase/"
        "2e718684-4f75-4a99-8d6b-3b6bd44e4228"
    )
    return _deferred_candidate(
        db_session,
        text="Supabase is hiring a Software Engineer",
        raw_payload={
            "url": url,
            "type": "job",
            "feed": "jobs",
            "title": "Supabase is hiring a Software Engineer",
            "url_classification": {
                "platform": "ashby",
                "external_company_slug": "supabase",
                "original_url": url,
            },
        },
        source_identifier=source_identifier,
        name="Supabase",
    )


@pytest.mark.asyncio
async def test_dexter_resolves_from_business_email(db_session):
    candidate = _deferred_candidate(db_session)
    service = CompanyDomainEnrichmentService(db_session, validator=FakeValidator())

    result = await service.enrich_candidate(candidate.id)

    assert result.decision == "created_company"
    assert result.resolved_domain == "getdexter.co"
    assert result.candidate.deferred_reason is None
    assert result.candidate.status == DiscoveryCandidateStatus.INGESTED
    assert result.attempts


@pytest.mark.asyncio
async def test_dexter_ignores_encoded_yc_url_and_resolves_email_domain(db_session):
    candidate = _deferred_candidate(
        db_session,
        (
            "Apply at jobs@getdexter.co. "
            "YC listing: https:&#x2F;&#x2F;www.ycombinator.com"
            "&#x2F;companies&#x2F;dexter&#x2F;jobs"
        ),
    )
    service = CompanyDomainEnrichmentService(db_session, validator=FakeValidator())

    result = await service.enrich_candidate(candidate.id)

    assert result.decision == "created_company"
    assert result.resolved_domain == "getdexter.co"
    assert result.candidate.deferred_reason is None
    assert result.attempts[-1].status == "resolved"
    assert result.attempts[-1].resolver == "business_email_domain"


@pytest.mark.asyncio
async def test_repeated_enrichment_does_not_duplicate_company(db_session):
    candidate = _deferred_candidate(db_session)
    service = CompanyDomainEnrichmentService(db_session, validator=FakeValidator())

    first = await service.enrich_candidate(candidate.id)
    second = await service.enrich_candidate(candidate.id)

    assert first.company_id == second.company_id
    assert service.company_repository.count_companies() == 1


@pytest.mark.asyncio
async def test_yc_profile_resolves_candidate_and_creates_company(db_session):
    candidate = _yc_candidate(db_session)
    yc_resolver = FakeYCResolver(_yc_resolution())
    service = CompanyDomainEnrichmentService(
        db_session, validator=FakeValidator(), yc_resolver=yc_resolver
    )

    result = await service.enrich_candidate(candidate.id)

    assert result.decision == "created_company"
    assert result.resolved_domain == "infracost.io"
    assert result.candidate.deferred_reason is None
    assert result.candidate.status == DiscoveryCandidateStatus.INGESTED
    assert result.attempts[-1].resolver == "ycombinator_profile"
    assert result.attempts[-1].evidence["yc_profile"]["company_slug"] == "infracost"
    assert yc_resolver.calls == 1


@pytest.mark.asyncio
async def test_yc_profile_matches_existing_company(db_session):
    candidate = _yc_candidate(db_session)
    db_session.add(
        Company(
            name="Infracost",
            website_url="https://www.infracost.io",
            normalized_domain="infracost.io",
            source="yc",
            stage="unknown",
            is_active=True,
        )
    )
    db_session.commit()
    service = CompanyDomainEnrichmentService(
        db_session, validator=FakeValidator(), yc_resolver=FakeYCResolver(_yc_resolution())
    )

    result = await service.enrich_candidate(candidate.id)

    assert result.decision == "matched_existing_company"
    assert result.resolved_domain == "infracost.io"
    assert service.company_repository.count_companies() == 1


@pytest.mark.asyncio
async def test_yc_profile_404_leaves_candidate_deferred(db_session):
    candidate = _yc_candidate(db_session)
    unresolved = _yc_resolution(resolved=False, reason="yc_profile_not_found")
    unresolved = YCCompanyResolutionResult(
        **{**unresolved.__dict__, "proposed_website_url": None, "proposed_domain": None}
    )
    service = CompanyDomainEnrichmentService(
        db_session, validator=FakeValidator(), yc_resolver=FakeYCResolver(unresolved)
    )

    result = await service.enrich_candidate(candidate.id)

    assert result.decision == "unresolved"
    assert result.candidate.decision == DiscoveryDecision.DEFERRED
    assert result.candidate.deferred_reason == "requires_company_domain_enrichment"
    assert result.attempts[-1].reason == "yc_profile_not_found"


@pytest.mark.asyncio
async def test_yc_profile_invalid_domain_leaves_candidate_deferred(db_session):
    candidate = _yc_candidate(db_session)
    service = CompanyDomainEnrichmentService(
        db_session,
        validator=FakeValidator(valid=False, reason="blocked_or_shared_domain"),
        yc_resolver=FakeYCResolver(_yc_resolution()),
    )

    result = await service.enrich_candidate(candidate.id)

    assert result.decision == "unresolved"
    assert result.attempts[-1].reason == "yc_profile_website_blocked"
    assert result.candidate.deferred_reason == "requires_company_domain_enrichment"


@pytest.mark.asyncio
async def test_yc_profile_result_reused_for_same_slug_in_run(db_session):
    first = _yc_candidate(db_session, "hn:yc-1")
    second = _yc_candidate(db_session, "hn:yc-2")
    db_session.query(DiscoveryCandidate).filter(
        DiscoveryCandidate.id == second.id
    ).update({"discovery_run_id": first.discovery_run_id})
    db_session.commit()
    yc_resolver = FakeYCResolver(_yc_resolution())
    service = CompanyDomainEnrichmentService(
        db_session, validator=FakeValidator(), yc_resolver=yc_resolver
    )

    result = await service.enrich_discovery_run(first.discovery_run_id)

    assert result.candidates_resolved == 2
    assert result.companies_created == 1
    assert result.companies_matched == 1
    assert yc_resolver.calls == 1
    assert service.company_repository.count_companies() == 1


@pytest.mark.asyncio
async def test_ashby_resolution_creates_company_attempt_and_focused_evidence(
    db_session,
):
    candidate = _ashby_candidate(db_session)
    resolver = FakeAshbyResolver()
    service = CompanyDomainEnrichmentService(
        db_session,
        validator=FakeValidator(),
        ashby_resolver=resolver,
    )

    result = await service.enrich_candidate(candidate.id)
    repeated = await service.enrich_candidate(candidate.id)

    assert result.decision == "created_company"
    assert repeated.company_id == result.company_id
    assert result.resolved_domain == "supabase.com"
    assert result.candidate.deferred_reason is None
    assert result.attempts[-1].resolver == "ashby_public_job_board"
    evidence = service.evidence_repository.list_by_candidate(candidate.id)
    assert [item.evidence_type for item in evidence] == ["ashby_job_posting"]
    assert evidence[0].title == "Software Engineer"
    assert service.company_repository.count_companies() == 1


@pytest.mark.asyncio
async def test_ashby_unresolved_candidate_stays_deferred(db_session):
    candidate = _ashby_candidate(db_session)
    service = CompanyDomainEnrichmentService(
        db_session,
        validator=FakeValidator(),
        ashby_resolver=FakeAshbyResolver(resolved=False),
    )

    result = await service.enrich_candidate(candidate.id)

    assert result.decision == "unresolved"
    assert result.candidate.decision == DiscoveryDecision.DEFERRED
    assert result.candidate.deferred_reason == "requires_company_domain_enrichment"
    assert result.attempts[-1].reason == "ashby_company_domain_missing"


@pytest.mark.asyncio
async def test_ashby_board_response_reused_by_slug(db_session):
    first = _ashby_candidate(db_session, "hn:ashby-1")
    second = _ashby_candidate(db_session, "hn:ashby-2")
    db_session.query(DiscoveryCandidate).filter(
        DiscoveryCandidate.id == second.id
    ).update({"discovery_run_id": first.discovery_run_id})
    db_session.commit()
    resolver = FakeAshbyResolver()
    service = CompanyDomainEnrichmentService(
        db_session,
        validator=FakeValidator(),
        ashby_resolver=resolver,
    )

    result = await service.enrich_discovery_run(first.discovery_run_id)

    assert result.candidates_resolved == 2
    assert resolver.fetch_calls == 1
    assert service.company_repository.count_companies() == 1
