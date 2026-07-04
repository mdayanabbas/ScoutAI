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
