import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.enrichment.domain_validator import DomainValidationResult
from app.enrichment.ashby_public_job_parser import AshbyPublicJob
from app.enrichment.resolvers import (
    AshbyCompanyResolutionResult,
    AshbyJobBoardResult,
    YCCompanyResolutionResult,
)
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_run import DiscoveryRun
from app.services.company_domain_enrichment_service import (
    CompanyDomainEnrichmentService,
)
from app.api.v1.company_enrichment import get_company_domain_enrichment_service
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
)


class FakeValidator:
    async def validate(self, value: str):
        domain = "supabase.com" if "supabase" in value else "infracost.io"
        return DomainValidationResult(
            valid=True,
            requested_url=value,
            final_url=f"https://{domain}",
            normalized_domain=domain,
            status_code=200,
        )


class FakeYCResolver:
    def supports(self, candidate):
        classification = (candidate.raw_payload or {}).get("url_classification") or {}
        return classification.get("platform") == "ycombinator"

    def extract_company_slug(self, candidate):
        return ((candidate.raw_payload or {}).get("url_classification") or {}).get(
            "external_company_slug"
        )

    async def resolve(self, candidate):
        return YCCompanyResolutionResult(
            resolved=True,
            company_slug="infracost",
            profile_url="https://www.ycombinator.com/companies/infracost",
            proposed_website_url="https://www.infracost.io",
            proposed_domain="infracost.io",
            reason="clearly labelled profile website link",
            status_code=200,
            confidence=0.95,
        )


class FakeAshbyResolver:
    def supports(self, candidate):
        classification = (candidate.raw_payload or {}).get("url_classification") or {}
        return classification.get("platform") == "ashby"

    def extract_board_slug(self, candidate):
        return "supabase"

    async def fetch_job_board(self, slug):
        return AshbyJobBoardResult(True, slug, 200, ())

    async def resolve(self, candidate, board_result=None):
        job = AshbyPublicJob(
            title="Software Engineer",
            location="Remote",
            secondary_locations=(),
            department="Engineering",
            team=None,
            is_listed=True,
            is_remote=True,
            workplace_type="Remote",
            description_plain="Email careers@supabase.com",
            description_html=None,
            published_at=None,
            employment_type="FullTime",
            job_url="https://jobs.ashbyhq.com/supabase/posting",
            apply_url=None,
            compensation_summary=None,
            raw_posting_id="posting",
        )
        return AshbyCompanyResolutionResult(
            True,
            board_slug="supabase",
            matched_job=job,
            proposed_website_url="supabase.com",
            proposed_domain="supabase.com",
            status_code=200,
            confidence=0.9,
            evidence={"listed_job_count": 1},
            reason="ashby_company_domain_evidence",
        )


@pytest.fixture
async def company_enrichment_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_missing_candidate_returns_404(company_enrichment_api_client: AsyncClient):
    response = await company_enrichment_api_client.post(
        "/api/v1/discovery/candidates/missing/enrich-domain"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_run_enrichment_resolves_yc_candidate(app, db_session):
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
    db_session.add(
        DiscoveryCandidate(
            discovery_run_id=run.id,
            source=DiscoverySource.HACKER_NEWS,
            source_identifier="hn:yc",
            raw_name="Infracost",
            raw_description="Apply through YC",
            normalized_name="Infracost",
            normalized_description="Apply through YC",
            status=DiscoveryCandidateStatus.NORMALIZED,
            decision=DiscoveryDecision.DEFERRED,
            deferred_reason="requires_company_domain_enrichment",
            raw_payload={
                "url_classification": {
                    "platform": "ycombinator",
                    "external_company_slug": "infracost",
                }
            },
        )
    )
    db_session.commit()

    def override_get_db():
        yield db_session

    def override_service():
        return CompanyDomainEnrichmentService(
            db_session, validator=FakeValidator(), yc_resolver=FakeYCResolver()
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_company_domain_enrichment_service] = override_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/discovery/runs/{run.id}/enrich-domains")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["candidates_resolved"] == 1
    assert data["companies_created"] == 1
    assert data["results"][0]["decision"] == "created_company"
    assert data["results"][0]["resolved_domain"] == "infracost.io"


@pytest.mark.asyncio
async def test_run_enrichment_automatically_resolves_ashby_candidate(
    app, db_session
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
    url = "https://jobs.ashbyhq.com/supabase/posting"
    db_session.add(
        DiscoveryCandidate(
            discovery_run_id=run.id,
            source=DiscoverySource.HACKER_NEWS,
            source_identifier="hn:ashby",
            raw_name="Supabase",
            raw_description="Supabase is hiring",
            normalized_name="Supabase",
            normalized_description="Supabase is hiring",
            status=DiscoveryCandidateStatus.NORMALIZED,
            decision=DiscoveryDecision.DEFERRED,
            deferred_reason="requires_company_domain_enrichment",
            raw_payload={
                "type": "job",
                "feed": "jobs",
                "url": url,
                "url_classification": {
                    "platform": "ashby",
                    "external_company_slug": "supabase",
                    "original_url": url,
                },
            },
        )
    )
    db_session.commit()

    def override_get_db():
        yield db_session

    def override_service():
        return CompanyDomainEnrichmentService(
            db_session,
            validator=FakeValidator(),
            ashby_resolver=FakeAshbyResolver(),
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_company_domain_enrichment_service] = override_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/discovery/runs/{run.id}/enrich-domains"
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["candidates_resolved"] == 1
    assert data["results"][0]["resolved_domain"] == "supabase.com"
    assert data["results"][0]["attempts"][-1]["resolver"] == (
        "ashby_public_job_board"
    )
