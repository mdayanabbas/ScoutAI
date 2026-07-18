from app.models.company import Company
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_matching_profile import JobMatchingProfile
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_matching_profile_repository import JobMatchingProfileRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.models.user_profile import UserProfile


def create_company(db_session, name: str = "Tether") -> Company:
    return CompanyRepository(db_session).create_company(
        Company(
            name=name,
            website_url=f"https://{name.lower().replace(' ', '-')}.example",
            normalized_domain=f"{name.lower().replace(' ', '-')}.example",
        )
    )


def create_company_job(db_session, company: Company, title: str = "AI Engineer") -> Job:
    return JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title=title,
            normalized_title=title.lower(),
            role_category="ai_engineer",
            remote_type="remote_worldwide",
            job_url=f"https://{company.normalized_domain}/jobs/{title.lower().replace(' ', '-')}",
            apply_url=f"https://{company.normalized_domain}/apply",
            status="active",
            enrichment_status="enriched",
        )
    )


def create_job_match(db_session, job: Job) -> JobMatch:
    user = UserProfileRepository(db_session).create_profile(UserProfile(display_name="Abbas"))
    profile = JobMatchingProfileRepository(db_session).create(
        JobMatchingProfile(user_profile_id=user.id)
    )
    match = JobMatch(
        job_id=job.id,
        job_matching_profile_id=profile.id,
        eligibility_status="eligible",
        remote_eligibility="work_from_anywhere",
        match_tier="strong_match",
        total_score=82,
        scoring_version="test",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match
