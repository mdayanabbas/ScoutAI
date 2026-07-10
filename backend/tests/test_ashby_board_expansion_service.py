from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.jobs.enrichment.providers.ashby_models import (
    AshbyPublicJobBoardResponse,
    AshbyPublicJobPosting,
)
from app.models.company import Company
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_run import DiscoveryRun
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_board_expansion_link_repository import JobBoardExpansionLinkRepository
from app.repositories.job_discovery_link_repository import JobDiscoveryLinkRepository
from app.repositories.job_enrichment_attempt_repository import JobEnrichmentAttemptRepository
from app.repositories.job_repository import JobRepository
from app.services.ashby_board_expansion_service import AshbyBoardExpansionService
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
    JobStatus,
)


@dataclass
class FakeClient:
    jobs: list[AshbyPublicJobPosting]
    reason: str | None = None

    async def list_published_jobs(self, board_slug: str, *, include_compensation: bool = True):
        return AshbyPublicJobBoardResponse(board_slug=board_slug, jobs=self.jobs, status_code=200, response_size=200, reason=self.reason)


def _posting(id: str, title: str, *, department=None, team=None, listed=True):
    return AshbyPublicJobPosting(
        id=id,
        title=title,
        department=department,
        team=team,
        is_listed=listed,
        location="Remote",
        workplace_type="Remote",
        employment_type="FullTime",
        description_plain=f"{title} role with customers. $100K - $150K",
        job_url=f"https://jobs.ashbyhq.com/lago/{id}",
    )


def _parent(db_session, *, title="GTM Team", description="Lago is hiring for our GTM team"):
    token = uuid4().hex[:8]
    company = CompanyRepository(db_session).create_company(
        Company(name=f"Lago {token}", website_url=f"https://getlago-{token}.com", normalized_domain=f"getlago-{token}.com")
    )
    run = DiscoveryRun(
        source=DiscoverySource.HACKER_NEWS,
        status=DiscoveryRunStatus.SUCCESS,
        candidates_found=1,
        candidates_normalized=1,
        companies_created=1,
        companies_matched=0,
        candidates_deferred=0,
        candidates_rejected=0,
        candidates_failed=0,
    )
    db_session.add(run)
    db_session.commit()
    candidate = DiscoveryCandidate(
        discovery_run_id=run.id,
        source=DiscoverySource.HACKER_NEWS,
        source_identifier=f"hn:{title}:{token}",
        raw_name="Lago",
        raw_description=description,
        normalized_name="Lago",
        normalized_description=description,
        status=DiscoveryCandidateStatus.INGESTED,
        decision=DiscoveryDecision.CREATED_COMPANY,
        matched_company_id=company.id,
        raw_payload={"title": description},
    )
    db_session.add(candidate)
    db_session.commit()
    parent = JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            discovery_candidate_id=candidate.id,
            title=title,
            normalized_title=title.lower(),
            description=description,
            job_url="https://jobs.ashbyhq.com/lago",
            source_platform="hacker_news",
            status=JobStatus.ACTIVE,
        )
    )
    JobDiscoveryLinkRepository(db_session).get_or_create_link(parent.id, candidate.id)
    return parent, candidate


@pytest.mark.asyncio
async def test_gtm_board_expansion_creates_relevant_jobs_and_deactivates_parent(db_session):
    parent, candidate = _parent(db_session)
    service = AshbyBoardExpansionService(
        db_session,
        client=FakeClient(
            [
                _posting("ae", "Account Executive", department="Sales"),
                _posting("growth", "Growth Marketing Lead", department="Marketing"),
                _posting("backend", "Backend Engineer", department="Engineering"),
            ]
        ),
    )

    result = await service.expand_job_board(parent.id)

    assert result.status == "succeeded"
    assert result.jobs_created == 2
    assert result.parent_deactivated is True
    assert JobRepository(db_session).get_by_id(parent.id).status == "inactive"
    assert JobDiscoveryLinkRepository(db_session).count_by_candidate_id(candidate.id) == 3
    assert len(JobBoardExpansionLinkRepository(db_session).list_children(parent.id)) == 2
    assert all("Backend Engineer" != item.title or not item.selected for item in result.candidates)
    attempt = JobEnrichmentAttemptRepository(db_session).get_by_id(result.attempt_id)
    assert attempt.status == "succeeded"
    assert "description_html" not in str(attempt.evidence_json)


@pytest.mark.asyncio
async def test_repeated_expansion_reuses_existing_jobs_without_duplicates(db_session):
    parent, candidate = _parent(db_session)
    service = AshbyBoardExpansionService(
        db_session,
        client=FakeClient([_posting("ae", "Account Executive", department="Sales")]),
    )

    first = await service.expand_job_board(parent.id)
    JobRepository(db_session).update_job(JobRepository(db_session).get_by_id(parent.id), {"status": JobStatus.ACTIVE})
    second = await service.expand_job_board(parent.id)

    assert first.jobs_created == 1
    assert second.jobs_existing == 1
    assert JobRepository(db_session).count_jobs() == 2
    assert JobDiscoveryLinkRepository(db_session).count_by_candidate_id(candidate.id) == 2
    assert len(JobBoardExpansionLinkRepository(db_session).list_children(parent.id)) == 1


@pytest.mark.asyncio
async def test_specific_role_skips_and_unknown_scope_unresolved(db_session):
    specific_parent, _ = _parent(db_session, title="Founding Backend Engineer", description="Founding Backend Engineer")
    specific = await AshbyBoardExpansionService(
        db_session,
        client=FakeClient([_posting("backend", "Backend Engineer", department="Engineering")]),
    ).expand_job_board(specific_parent.id)
    assert specific.status == "skipped"
    assert specific.reason == "specific_role_should_use_job_enrichment"

    unknown_parent, _ = _parent(db_session, title="Lago", description="Lago update")
    unknown = await AshbyBoardExpansionService(
        db_session,
        client=FakeClient([_posting("ae", "Account Executive", department="Sales")]),
    ).expand_job_board(unknown_parent.id)
    assert unknown.status == "unresolved"
    assert unknown.reason == "ashby_expansion_scope_unknown"
    assert JobRepository(db_session).get_by_id(unknown_parent.id).status == "active"


@pytest.mark.asyncio
async def test_exact_posting_and_provider_failure_do_not_create_children(db_session):
    exact_parent, _ = _parent(db_session)
    JobRepository(db_session).update_job(exact_parent, {"job_url": "https://jobs.ashbyhq.com/lago/ae"})

    exact = await AshbyBoardExpansionService(db_session, client=FakeClient([])).expand_job_board(exact_parent.id)
    assert exact.status == "skipped"
    assert exact.reason == "exact_posting_should_use_job_enrichment"

    failed_parent, _ = _parent(db_session, title="Engineering Team", description="Engineering team")
    failed = await AshbyBoardExpansionService(
        db_session,
        client=FakeClient([], reason="ashby_rate_limited"),
    ).expand_job_board(failed_parent.id)
    assert failed.status == "failed"
    assert JobRepository(db_session).get_by_id(failed_parent.id).status == "active"
