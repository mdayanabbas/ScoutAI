from datetime import datetime, timezone

import app.models  # noqa: F401
from app.db.base import Base
from app.models import Job, JobEnrichmentAttempt
from app.utils.enums import JobEnrichmentAttemptStatus, JobEnrichmentStatus


def test_job_enrichment_attempt_model_registered():
    assert JobEnrichmentAttempt
    assert "job_enrichment_attempts" in Base.metadata.tables


def test_job_has_enrichment_columns():
    table = Base.metadata.tables["jobs"]
    required = {
        "seniority",
        "employment_type",
        "apply_url",
        "published_at",
        "last_verified_at",
        "salary_text",
        "equity_mentioned",
        "visa_sponsorship",
        "work_authorization",
        "required_skills_json",
        "preferred_skills_json",
        "technologies_json",
        "enrichment_status",
        "enrichment_confidence",
        "enriched_at",
    }

    assert required.issubset(table.columns.keys())
    for column_name in required - {"enrichment_status"}:
        assert table.columns[column_name].nullable is True
    assert table.columns["enrichment_status"].nullable is False
    assert table.columns["enrichment_status"].type.length >= 32


def test_job_defaults_to_not_enriched_and_json_fields_are_mutable_safe():
    first = Job(company_id="company-1", title="Engineer", job_url="jobs.example/1")
    second = Job(company_id="company-1", title="Designer", job_url="jobs.example/2")

    assert first.enrichment_status is None or first.enrichment_status == JobEnrichmentStatus.NOT_ENRICHED
    assert first.required_skills_json is None
    assert second.required_skills_json is None
    first.required_skills_json = ["python"]

    assert second.required_skills_json is None


def test_job_json_fields_accept_lists_and_timestamps_are_timezone_aware():
    now = datetime.now(timezone.utc)
    job = Job(
        company_id="company-1",
        title="Engineer",
        job_url="jobs.example/1",
        required_skills_json=["python"],
        preferred_skills_json=["postgres"],
        technologies_json=["fastapi"],
        published_at=now,
        last_verified_at=now,
        enriched_at=now,
    )

    assert job.required_skills_json == ["python"]
    assert job.published_at.tzinfo is not None
    assert job.last_verified_at.tzinfo is not None
    assert job.enriched_at.tzinfo is not None


def test_attempt_status_values_fit_columns():
    table = Base.metadata.tables["job_enrichment_attempts"]

    assert table.columns["provider"].type.length >= 64
    assert table.columns["status"].type.length >= 32
    assert all(len(item.value) <= table.columns["status"].type.length for item in JobEnrichmentAttemptStatus)
