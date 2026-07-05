import pytest

from app.core.errors import NotFoundError
from app.services.company_service import CompanyService
from app.services.job_service import JobService
from app.utils.enums import JobStatus


def test_job_create_or_update_deduplicates_and_normalizes_title(db_session):
    company = CompanyService(db_session).create_company(
        {"name": "Jobs Co", "website_url": "https://jobs.example"}
    )
    service = JobService(db_session)

    job = service.create_or_update_job(
        company.id,
        {
            "title": "  Senior   AI Engineer ",
            "job_url": "https://www.jobs.example/openings/1/",
            "status": JobStatus.ACTIVE,
        },
    )
    updated = service.create_or_update_job(
        company.id,
        {
            "title": "Principal AI Engineer",
            "job_url": "http://jobs.example/openings/1",
            "status": JobStatus.ACTIVE,
        },
    )

    assert updated.id == job.id
    assert updated.normalized_title == "principal ai engineer"
    assert updated.last_seen_at is not None
    assert service.count_jobs(company_id=company.id) == 1


def test_job_service_missing_company_and_job_raise_not_found(db_session):
    service = JobService(db_session)

    with pytest.raises(NotFoundError):
        service.create_or_update_job("missing", {"title": "Engineer"})

    with pytest.raises(NotFoundError):
        service.get_job("missing")
