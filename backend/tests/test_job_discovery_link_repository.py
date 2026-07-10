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
    company = CompanyRepository(db_session).create_company(
        Company(
            name="Link Co",
            website_url="https://link.example",
            normalized_domain="link.example",
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
        source_identifier="hn:link",
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
