from datetime import datetime, timezone

import pytest

from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_evidence import DiscoveryEvidence
from app.models.discovery_run import DiscoveryRun
from app.models.job_discovery_link import JobDiscoveryLink
from app.services.company_service import CompanyService
from app.services.discovery_job_ingestion_service import DiscoveryJobIngestionService
from app.services.job_service import JobService
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryDecision, DiscoveryRunStatus, DiscoverySource
from app.utils.urls import normalize_url


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


def _resolved_candidate(
    db_session,
    title="Dexter (YC F24) Is Hiring a Founding Engineer in Berlin",
    description="Location: Berlin\nApply at https://www.ycombinator.com/companies/dexter/jobs/1",
):
    company = CompanyService(db_session).create_company(
        {"name": "Dexter", "website_url": "https://getdexter.co"}
    )
    run = _run(db_session)
    candidate = DiscoveryCandidate(
        discovery_run_id=run.id,
        source=DiscoverySource.HACKER_NEWS,
        source_identifier="hn:123",
        raw_name="Dexter",
        raw_description=description,
        normalized_name="Dexter",
        normalized_description=description,
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


def _resolved_candidate_for_company(
    db_session,
    company,
    *,
    run=None,
    source_identifier="hn:123",
    title="Dexter (YC F24) Is Hiring a Founding Engineer in Berlin",
    description="Location: Berlin\nApply at https://www.ycombinator.com/companies/dexter/jobs/1",
):
    run = run or _run(db_session)
    candidate = DiscoveryCandidate(
        discovery_run_id=run.id,
        source=DiscoverySource.HACKER_NEWS,
        source_identifier=source_identifier,
        raw_name=company.name,
        raw_description=description,
        normalized_name=company.name,
        normalized_description=description,
        status=DiscoveryCandidateStatus.INGESTED,
        decision=DiscoveryDecision.MATCHED_EXISTING_COMPANY,
        matched_company_id=company.id,
        raw_payload={
            "id": source_identifier,
            "type": "job",
            "feed": "jobs",
            "title": title,
            "url": None,
        },
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


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
    links = db_session.query(JobDiscoveryLink).all()
    assert len(links) == 1
    assert links[0].job_id == result.job.id
    assert links[0].discovery_candidate_id == candidate.id


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
    assert db_session.query(JobDiscoveryLink).filter_by(
        job_id=result.job.id,
        discovery_candidate_id=candidate.id,
    ).one()


def test_cross_run_canonical_match_preserves_original_discovery_candidate(db_session):
    candidate, company, _run_obj = _resolved_candidate(
        db_session,
        title="9 Mothers Is Hiring a Founding Engineer",
        description="Apply at https://9mothers.com/careers",
    )
    service = DiscoveryJobIngestionService(db_session)
    first = service.ingest_candidate(candidate.id)
    original_updated_at = first.job.updated_at
    second = _resolved_candidate_for_company(
        db_session,
        company,
        source_identifier="hn:456",
        title="9 Mothers Is Hiring a Founding Engineer",
        description="Apply at https://9mothers.com/careers/",
    )

    result = service.ingest_candidate(second.id)

    assert result.action == "already_exists"
    assert result.job_id == first.job_id
    assert result.job.discovery_candidate_id == candidate.id
    assert result.job.created_at == first.job.created_at
    assert result.job.updated_at != original_updated_at
    links = db_session.query(JobDiscoveryLink).filter_by(job_id=first.job_id).all()
    assert {link.discovery_candidate_id for link in links} == {candidate.id, second.id}


def test_job_url_normalization_equivalent_urls_match():
    assert normalize_url("https://9mothers.com/careers") == "9mothers.com/careers"
    assert normalize_url("9mothers.com/careers") == "9mothers.com/careers"
    assert normalize_url("https://9mothers.com/careers/") == "9mothers.com/careers"
    assert normalize_url("https://9MOTHERS.com:443/careers#apply") == "9mothers.com/careers"
    assert normalize_url("http://9mothers.com:80/careers") == "9mothers.com/careers"
    assert normalize_url("9mothers.com:443/careers") == "9mothers.com/careers"
    assert normalize_url("https://9mothers.com/jobs") != "9mothers.com/careers"


def test_candidate_link_returns_already_exists_without_duplicate_job(db_session):
    candidate, _company, _run_obj = _resolved_candidate(db_session)
    service = DiscoveryJobIngestionService(db_session)
    first = service.ingest_candidate(candidate.id)

    second = service.ingest_candidate(candidate.id)

    assert second.action == "already_exists"
    assert second.job_id == first.job_id
    assert service.job_repository.count_jobs() == 1


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


def test_resolved_ashby_candidate_uses_focused_posting_evidence(db_session):
    candidate, _company, _run_obj = _resolved_candidate(db_session)
    db_session.add(
        DiscoveryEvidence(
            discovery_candidate_id=candidate.id,
            evidence_type="ashby_job_posting",
            source_url="https://jobs.ashbyhq.com/acme/posting-id",
            title="Exact Ashby Platform Engineer",
            excerpt="Short excerpt",
            published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            metadata_json={
                "identity": "posting-id",
                "description_plain": "Full Ashby job description",
                "location": "New York",
                "workplace_type": "Hybrid",
                "is_remote": False,
                "employment_type": "FullTime",
                "job_url": "https://jobs.ashbyhq.com/acme/posting-id",
                "apply_url": "https://jobs.ashbyhq.com/acme/posting-id/application",
                "published_at": "2026-07-01T00:00:00+00:00",
            },
        )
    )
    db_session.commit()

    result = DiscoveryJobIngestionService(db_session).ingest_candidate(candidate.id)

    assert result.action == "created"
    assert result.job is not None
    assert result.job.title == "Exact Ashby Platform Engineer"
    assert result.job.description == "Full Ashby job description"
    assert result.job.location == "New York"
    assert result.job.remote_type == "hybrid"
    assert result.job.source_platform == "ashby"
    assert result.job.job_url == "jobs.ashbyhq.com/acme/posting-id"
