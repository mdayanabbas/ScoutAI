from datetime import datetime, timedelta, timezone

import pytest

from app.models.company import Company
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.utils.enums import JobStatus, RemoteType, RoleCategory


def test_job_repository_create_lookup_list_count_active(db_session):
    company = CompanyRepository(db_session).create_company(
        Company(name="Jobs Co", normalized_domain="jobs.example")
    )
    repo = JobRepository(db_session)
    job = repo.create_job(
        Job(
            company_id=company.id,
            title="AI Engineer",
            normalized_title="ai engineer",
            role_category=RoleCategory.AI_ENGINEER,
            remote_type=RemoteType.REMOTE_WORLDWIDE,
            status=JobStatus.ACTIVE,
            job_url="https://jobs.example/ai-engineer",
        )
    )

    assert repo.get_by_id(job.id) == job
    assert repo.get_by_company_and_url(company.id, "https://jobs.example/ai-engineer") == job
    assert repo.list_jobs(company_id=company.id, search="engineer") == [job]
    assert repo.list_active_jobs(company_id=company.id) == [job]
    assert repo.count_jobs(role_category=RoleCategory.AI_ENGINEER, status=JobStatus.ACTIVE) == 1

    repo.update_job(job, {"status": JobStatus.INACTIVE})
    assert repo.list_active_jobs(company_id=company.id) == []

    repo.delete_job(job)
    assert repo.count_jobs(company_id=company.id) == 0


def _company(db_session):
    return CompanyRepository(db_session).create_company(
        Company(name="Enrichment Jobs Co", normalized_domain="enrichment-jobs.example")
    )


def _job(db_session, company, title, status="not_enriched", verified_at=None, created_at=None):
    return JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title=title,
            normalized_title=title.lower(),
            status=JobStatus.ACTIVE,
            job_url=f"https://jobs.example/{title.lower().replace(' ', '-')}",
            enrichment_status=status,
            last_verified_at=verified_at,
            created_at=created_at or datetime.now(timezone.utc),
        )
    )


def test_list_jobs_needing_enrichment_filters_and_orders(db_session):
    company = _company(db_session)
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    never = _job(db_session, company, "Never", "not_enriched", None, old)
    partial = _job(db_session, company, "Partial", "partially_enriched", old, now)
    unresolved = _job(db_session, company, "Unresolved", "unresolved", old, now)
    _job(db_session, company, "Enriched", "enriched", now, now)
    _job(db_session, company, "Failed", "failed", None, now)

    jobs = JobRepository(db_session).list_jobs_needing_enrichment()

    assert [job.id for job in jobs] == [never.id, partial.id, unresolved.id]


def test_update_enrichment_fields_allows_only_enrichment_fields(db_session):
    company = _company(db_session)
    job = _job(db_session, company, "Safe")
    repo = JobRepository(db_session)
    verified_at = datetime.now(timezone.utc)

    updated = repo.update_enrichment_fields(
        job.id,
        {
            "seniority": "senior",
            "required_skills_json": ["python"],
            "enrichment_status": "enriched",
            "enrichment_confidence": 0.92,
            "last_verified_at": verified_at,
            "enriched_at": verified_at,
        },
    )

    assert updated.seniority == "senior"
    assert updated.required_skills_json == ["python"]
    assert updated.enrichment_status == "enriched"
    assert updated.last_verified_at == verified_at.replace(tzinfo=None)


def test_update_enrichment_fields_stamps_successful_checks(db_session):
    company = _company(db_session)
    job = _job(db_session, company, "Stamped")

    updated = JobRepository(db_session).update_enrichment_fields(
        job.id,
        {
            "enrichment_status": "enriched",
            "employment_type": "full_time",
        },
    )

    assert updated.enrichment_status == "enriched"
    assert updated.last_verified_at is not None
    assert updated.enriched_at is not None


@pytest.mark.parametrize(
    "field",
    ["company_id", "discovery_candidate_id", "created_at", "first_seen_at", "unknown"],
)
def test_update_enrichment_fields_rejects_immutable_or_unknown_fields(db_session, field):
    company = _company(db_session)
    job = _job(db_session, company, "Unsafe")

    with pytest.raises(ValueError):
        JobRepository(db_session).update_enrichment_fields(job.id, {field: "nope"})


def test_mark_enrichment_status_helpers(db_session):
    company = _company(db_session)
    job = _job(db_session, company, "Status")
    repo = JobRepository(db_session)

    assert repo.mark_enrichment_pending(job.id).enrichment_status == "pending"
    assert repo.mark_enrichment_unresolved(job.id).enrichment_status == "unresolved"
    assert repo.mark_enrichment_failed(job.id).enrichment_status == "failed"
