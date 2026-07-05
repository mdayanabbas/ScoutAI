from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.job import JobCreate, JobRead, JobUpdate


class JobObj:
    id = "job-1"
    company_id = "company-1"
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
    created_at = datetime.now(timezone.utc)
    updated_at = None


def test_job_create_requires_title_and_job_url():
    with pytest.raises(ValidationError):
        JobCreate(title="AI Engineer")


def test_job_update_allows_partial_update():
    assert JobUpdate(title="New").title == "New"


def test_job_read_supports_from_attributes():
    assert JobRead.model_validate(JobObj()).normalized_title == "ai engineer"


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
