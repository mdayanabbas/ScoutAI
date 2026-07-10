from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.models.company import Company
from app.models.job import Job
from app.models.job_enrichment_attempt import JobEnrichmentAttempt
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_enrichment_attempt_repository import (
    JobEnrichmentAttemptRepository,
)
from app.repositories.job_repository import JobRepository
from app.utils.enums import JobEnrichmentAttemptStatus


def _job(db_session):
    company = CompanyRepository(db_session).create_company(
        Company(name="Enrich Co", normalized_domain="enrich.example")
    )
    return JobRepository(db_session).create_job(
        Job(company_id=company.id, title="Engineer", normalized_title="engineer", job_url="enrich.example/jobs/1")
    )


def _attempt(job_id, provider="first_party_job_page", created_at=None):
    return JobEnrichmentAttempt(
        job_id=job_id,
        provider=provider,
        status=JobEnrichmentAttemptStatus.RUNNING.value,
        source_url="https://enrich.example/jobs/1",
        started_at=created_at or datetime.now(timezone.utc),
        created_at=created_at or datetime.now(timezone.utc),
    )


def test_can_create_running_attempt_and_mark_completion_states(db_session):
    job = _job(db_session)
    repo = JobEnrichmentAttemptRepository(db_session)

    attempt = repo.create_attempt(_attempt(job.id))
    succeeded = repo.mark_succeeded(
        attempt,
        extracted_data={"title": "Engineer"},
        evidence={"title_source": "h1"},
        field_confidence={"title": 0.95},
    )

    assert succeeded.status == "succeeded"
    assert succeeded.finished_at is not None
    assert succeeded.extracted_data_json == {"title": "Engineer"}

    partial = repo.mark_partial(repo.create_attempt(_attempt(job.id)), reason="missing salary")
    unresolved = repo.mark_unresolved(repo.create_attempt(_attempt(job.id)), reason="not found")
    failed = repo.mark_failed(repo.create_attempt(_attempt(job.id)), "  boom  ")

    assert partial.status == "partial"
    assert unresolved.status == "unresolved"
    assert failed.status == "failed"
    assert failed.error_message == "boom"


def test_long_provider_values_fit_and_attempts_are_newest_first(db_session):
    job = _job(db_session)
    repo = JobEnrichmentAttemptRepository(db_session)
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = old + timedelta(days=1)

    first = repo.create_attempt(_attempt(job.id, "deterministic_fallback", old))
    second = repo.create_attempt(
        _attempt(job.id, "ycombinator_job_page_with_extra_context", new)
    )

    attempts = repo.list_by_job_id(job.id)

    assert [attempt.id for attempt in attempts] == [second.id, first.id]
    assert repo.get_latest_for_job(job.id).id == second.id
    assert repo.get_latest_by_provider(job.id, "deterministic_fallback").id == first.id


def test_deleting_job_cascades_attempts(db_session):
    db_session.execute(text("PRAGMA foreign_keys=ON"))
    job = _job(db_session)
    repo = JobEnrichmentAttemptRepository(db_session)
    repo.create_attempt(_attempt(job.id))

    JobRepository(db_session).delete_job(job)

    assert repo.list_by_job_id(job.id) == []
