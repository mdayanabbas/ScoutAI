from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.job import JobCreate, JobRead, JobUpdate


class CompanyObj:
    name = "Acme AI"
    website_url = "acme.ai"


class JobObj:
    id = "job-1"
    company_id = "company-1"
    company = CompanyObj()
    discovery_candidate_id = None
    title = "AI Engineer"
    normalized_title = "ai engineer"
    role_category = "other"
    description = "Build things"
    location = None
    remote_type = "unknown"
    experience_min = None
    experience_max = None
    salary_min = None
    salary_max = None
    salary_currency = None
    job_url = "https://acme.ai/jobs/1"
    source_platform = None
    status = "active"
    first_seen_at = None
    last_seen_at = None
    seniority = "senior"
    employment_type = "full_time"
    apply_url = "https://acme.ai/apply"
    published_at = None
    last_verified_at = None
    salary_text = None
    equity_mentioned = True
    visa_sponsorship = None
    work_authorization = None
    required_skills_json = ["python"]
    preferred_skills_json = None
    technologies_json = ["fastapi"]
    enrichment_status = "enriched"
    enrichment_confidence = 0.9
    enriched_at = None
    created_at = datetime.now(timezone.utc)
    updated_at = None


class BrokenCompanyJobObj(JobObj):
    @property
    def company(self):
        raise RuntimeError("company relationship unavailable")


def test_job_create_requires_title_and_job_url():
    with pytest.raises(ValidationError):
        JobCreate(title="AI Engineer")


def test_job_update_allows_partial_update():
    assert JobUpdate(title="New").title == "New"


def test_job_read_supports_from_attributes():
    job = JobRead.model_validate(JobObj())

    assert job.normalized_title == "ai engineer"
    assert job.company_name == "Acme AI"
    assert job.company_website_url == "acme.ai"
    assert job.enrichment_status == "enriched"
    assert job.required_skills_json == ["python"]


def test_job_read_uses_null_company_fields_when_relationship_unavailable():
    job = JobRead.model_validate(BrokenCompanyJobObj())

    assert job.company_name is None
    assert job.company_website_url is None


def test_invalid_experience_range_fails():
    with pytest.raises(ValidationError):
        JobCreate(
            title="AI Engineer",
            job_url="https://acme.ai/jobs/1",
            experience_min=5,
            experience_max=2,
        )


def test_invalid_salary_range_fails():
    with pytest.raises(ValidationError):
        JobCreate(
            title="AI Engineer",
            job_url="https://acme.ai/jobs/1",
            salary_min=200,
            salary_max=100,
        )


def test_job_enrichment_attempt_read_maps_internal_json_fields():
    from app.schemas.job import JobEnrichmentAttemptRead

    now = datetime.now(timezone.utc)
    data = JobEnrichmentAttemptRead.model_validate(
        {
            "id": "attempt-1",
            "job_id": "job-1",
            "provider": "first_party_job_page",
            "status": "succeeded",
            "extracted_data_json": {"title": "Engineer"},
            "evidence_json": {"source": "h1"},
            "field_confidence_json": {"title": 0.9},
            "started_at": now,
            "created_at": now,
        }
    )

    assert data.extracted_data == {"title": "Engineer"}
    assert data.evidence == {"source": "h1"}
    assert data.field_confidence == {"title": 0.9}
