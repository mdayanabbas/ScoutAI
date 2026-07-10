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
    assert updated.job_url == "https://jobs.example/openings/1"
    assert updated.enrichment_status == "not_enriched"
    assert updated.last_seen_at is not None
    assert service.count_jobs(company_id=company.id) == 1


def test_job_service_normalizes_apply_url_and_ignores_invalid_job_url_update(db_session):
    company = CompanyService(db_session).create_company(
        {"name": "Nine Mothers", "website_url": "https://9mothers.com"}
    )
    service = JobService(db_session)
    job = service.create_or_update_job(
        company.id,
        {
            "title": "Founding Engineer",
            "job_url": "9mothers.com/careers/",
            "apply_url": "https://9mothers.com/apply/?utm_source=hn",
        },
    )

    updated = service.update_job(job.id, {"job_url": "javascript:alert(1)"})

    assert job.job_url == "https://9mothers.com/careers"
    assert job.apply_url == "https://9mothers.com/apply"
    assert updated.job_url == "https://9mothers.com/careers"


def test_job_service_missing_company_and_job_raise_not_found(db_session):
    service = JobService(db_session)

    with pytest.raises(NotFoundError):
        service.create_or_update_job("missing", {"title": "Engineer"})

    with pytest.raises(NotFoundError):
        service.get_job("missing")
