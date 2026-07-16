from app.models.company import Company
from app.models.job import Job
from app.models.user_profile import UserProfile
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.utils.enums import JobStatus


def create_user_profile(db_session, name: str = "Abbas") -> UserProfile:
    return UserProfileRepository(db_session).create_profile(UserProfile(display_name=name))


def create_job(db_session, *, title: str = "AI Engineer") -> Job:
    company = CompanyRepository(db_session).create_company(
        Company(
            name=f"{title} Co",
            normalized_domain=f"{abs(hash(title)) % 10_000_000}.example",
        )
    )
    return JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title=title,
            normalized_title=title.lower(),
            role_category="ai_engineer",
            remote_type="remote_worldwide",
            job_url=f"https://{company.normalized_domain}/jobs/1",
            status=JobStatus.ACTIVE,
            enrichment_status="enriched",
        )
    )
