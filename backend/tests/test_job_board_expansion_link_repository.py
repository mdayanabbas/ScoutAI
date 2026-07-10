from uuid import uuid4

from app.models.company import Company
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_run import DiscoveryRun
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_board_expansion_link_repository import (
    JobBoardExpansionLinkRepository,
)
from app.repositories.job_repository import JobRepository
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
)


def _objects(db_session):
    token = uuid4().hex[:8]
    company = CompanyRepository(db_session).create_company(
        Company(name=f"Expansion Co {token}", website_url=f"https://expansion-{token}.example", normalized_domain=f"expansion-{token}.example")
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
        source_identifier=f"hn:expansion:{token}",
        raw_name="Expansion Co",
        raw_description="Expansion Co is hiring",
        normalized_name="Expansion Co",
        normalized_description="Expansion Co is hiring",
        status=DiscoveryCandidateStatus.INGESTED,
        decision=DiscoveryDecision.CREATED_COMPANY,
        matched_company_id=company.id,
    )
    db_session.add(candidate)
    db_session.commit()
    parent = JobRepository(db_session).create_job(Job(company_id=company.id, title="GTM Team", normalized_title="gtm team", job_url=f"https://jobs.ashbyhq.com/expansion-{token}"))
    child = JobRepository(db_session).create_job(Job(company_id=company.id, title="Account Executive", normalized_title="account executive", job_url=f"https://jobs.ashbyhq.com/expansion-{token}/ae"))
    return parent, child, candidate


def test_expansion_link_repository_idempotent_lists(db_session):
    parent, child, candidate = _objects(db_session)
    repo = JobBoardExpansionLinkRepository(db_session)

    first = repo.get_or_create_link(parent_job_id=parent.id, child_job_id=child.id, discovery_candidate_id=candidate.id, provider="ashby_board_expansion")
    second = repo.get_or_create_link(parent_job_id=parent.id, child_job_id=child.id, discovery_candidate_id=candidate.id, provider="ashby_board_expansion")

    assert first.id == second.id
    assert repo.exists(parent.id, child.id)
    assert repo.list_children(parent.id)[0].child_job_id == child.id
    assert repo.list_parents(child.id)[0].parent_job_id == parent.id
