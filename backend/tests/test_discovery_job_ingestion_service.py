from datetime import datetime, timezone

import pytest

from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_run import DiscoveryRun
from app.services.company_service import CompanyService
from app.services.discovery_job_ingestion_service import DiscoveryJobIngestionService
from app.services.job_service import JobService
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryDecision, DiscoveryRunStatus, DiscoverySource


def _run(db_session):
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
    return run


def _resolved_candidate(db_session, title="Dexter (YC F24) Is Hiring a Founding Engineer in Berlin"):
    company = CompanyService(db_session).create_company(
        {"name": "Dexter", "website_url": "https://getdexter.co"}
    )
    run = _run(db_session)
    candidate = DiscoveryCandidate(
        discovery_run_id=run.id,
        source=DiscoverySource.HACKER_NEWS,
        source_identifier="hn:123",
        raw_name="Dexter",
        raw_description="Location: Berlin\nApply at https://www.ycombinator.com/companies/dexter/jobs/1",
        normalized_name="Dexter",
        normalized_description="Location: Berlin\nApply at https://www.ycombinator.com/companies/dexter/jobs/1",
        status=DiscoveryCandidateStatus.INGESTED,
        decision=DiscoveryDecision.CREATED_COMPANY,
        matched_company_id=company.id,
        raw_payload={
            "id": 123,
            "type": "job",
            "feed": "jobs",
            "title": title,
            "url": None,
        },
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate, company, run


def test_creates_job_for_resolved_hacker_news_candidate(db_session):
    candidate, company, _run_obj = _resolved_candidate(db_session)
    service = DiscoveryJobIngestionService(db_session)

    result = service.ingest_candidate(candidate.id)

    assert result.action == "created"
    assert result.company_id == company.id
    assert result.job is not None
    assert result.job.discovery_candidate_id == candidate.id
    assert result.job.title == "Founding Engineer"
    assert result.job.location == "Berlin"
    assert result.job.source_platform == "hacker_news"


def test_repeated_ingestion_does_not_duplicate_job(db_session):
    candidate, _company, _run_obj = _resolved_candidate(db_session)
    service = DiscoveryJobIngestionService(db_session)

    first = service.ingest_candidate(candidate.id)
    second = service.ingest_candidate(candidate.id)

    assert first.action == "created"
    assert second.action == "already_exists"
    assert service.job_repository.count_jobs() == 1


def test_legacy_job_can_be_associated(db_session):
    candidate, company, _run_obj = _resolved_candidate(db_session)
    JobService(db_session).create_or_update_job(
        company.id,
        {
            "title": "Founding Engineer",
            "job_url": "https://www.ycombinator.com/companies/dexter/jobs/1",
            "first_seen_at": datetime.now(timezone.utc),
        },
    )

    result = DiscoveryJobIngestionService(db_session).ingest_candidate(candidate.id)

    assert result.action == "already_exists"
    assert result.job is not None
    assert result.job.discovery_candidate_id == candidate.id


def test_unresolved_candidate_is_skipped(db_session):
    candidate, _company, _run_obj = _resolved_candidate(db_session)
    candidate.status = DiscoveryCandidateStatus.NORMALIZED
    candidate.decision = DiscoveryDecision.DEFERRED
    candidate.matched_company_id = None
    db_session.commit()

    result = DiscoveryJobIngestionService(db_session).ingest_candidate(candidate.id)

    assert result.action == "skipped"


def test_run_ingestion_returns_counters(db_session):
    _candidate, _company, run = _resolved_candidate(db_session)

    result = DiscoveryJobIngestionService(db_session).ingest_discovery_run(run.id)

    assert result.candidates_examined == 1
    assert result.jobs_created == 1
    assert result.candidates_skipped == 0
