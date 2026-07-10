from uuid import uuid4

from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_run import DiscoveryRun
from app.models.company import Company
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_discovery_link_repository import JobDiscoveryLinkRepository
from app.repositories.job_repository import JobRepository
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
)


def _candidate_and_job(db_session):
    token = uuid4().hex[:8]
    company = CompanyRepository(db_session).create_company(
        Company(
            name=f"Link Co {token}",
            website_url=f"https://link-{token}.example",
            normalized_domain=f"link-{token}.example",
        )
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
    db_session.refresh(run)
    candidate = DiscoveryCandidate(
        discovery_run_id=run.id,
        source=DiscoverySource.HACKER_NEWS,
        source_identifier=f"hn:link:{token}",
        raw_name="Link Co",
        raw_description="Link Co is hiring",
        normalized_name="Link Co",
        normalized_description="Link Co is hiring",
        status=DiscoveryCandidateStatus.INGESTED,
        decision=DiscoveryDecision.CREATED_COMPANY,
        matched_company_id=company.id,
        raw_payload={"type": "job", "feed": "jobs", "title": "Link Co is hiring"},
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    job = JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            discovery_candidate_id=candidate.id,
            title="Open Roles",
            normalized_title="open roles",
            job_url="link.example/jobs",
        )
    )
    return candidate, job


def test_ensure_link_creates_and_reuses_link(db_session):
    candidate, job = _candidate_and_job(db_session)
    repo = JobDiscoveryLinkRepository(db_session)

    first = repo.ensure_link(job.id, candidate.id)
    second = repo.ensure_link(job.id, candidate.id)

    assert first.id == second.id
    assert first.job_id == job.id
    assert first.discovery_candidate_id == candidate.id


def test_get_by_candidate_loads_job(db_session):
    candidate, job = _candidate_and_job(db_session)
    repo = JobDiscoveryLinkRepository(db_session)
    repo.ensure_link(job.id, candidate.id)

    link = repo.get_by_candidate_id(candidate.id)

    assert link is not None
    assert link.job.id == job.id


def test_candidate_can_link_to_multiple_jobs_and_job_to_multiple_candidates(db_session):
    candidate, job = _candidate_and_job(db_session)
    repo = JobDiscoveryLinkRepository(db_session)
    other_job = JobRepository(db_session).create_job(
        Job(
            company_id=job.company_id,
            title="Backend Engineer",
            normalized_title="backend engineer",
            job_url=f"https://jobs.ashbyhq.com/link/{uuid4().hex[:8]}",
        )
    )
    other_candidate, _ = _candidate_and_job(db_session)

    first = repo.get_or_create_link(job.id, candidate.id)
    second = repo.get_or_create_link(other_job.id, candidate.id)
    third = repo.get_or_create_link(job.id, other_candidate.id)
    duplicate = repo.get_or_create_link(other_job.id, candidate.id)

    assert first.id != second.id
    assert duplicate.id == second.id
    assert {link.job_id for link in repo.list_by_candidate_id(candidate.id)} == {job.id, other_job.id}
    assert {link.discovery_candidate_id for link in repo.list_by_job_id(job.id)} == {candidate.id, other_candidate.id}
    assert repo.count_by_candidate_id(candidate.id) == 2
