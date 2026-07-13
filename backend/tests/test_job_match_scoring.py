from app.models.company import Company
from app.models.job import Job
from app.models.job_matching_profile import JobMatchingProfile
from app.models.user_profile import UserProfile
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.services.job_matching_service import JobMatchingService
from app.utils.enums import JobStatus


def _profile(db_session):
    user = UserProfileRepository(db_session).create_profile(UserProfile(display_name="Abbas"))
    profile = JobMatchingProfile(user_profile_id=user.id, preferred_countries_json=["India"], work_authorization_countries_json=["India"], willing_to_relocate=False, accepted_employment_types_json=["full_time"])
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def _job(db_session, title, description, **kwargs):
    company = CompanyRepository(db_session).create_company(Company(name=title, normalized_domain=f"{abs(hash(title + description)) % 9999999}.example"))
    values = {
        "company_id": company.id,
        "title": title,
        "normalized_title": title.lower(),
        "role_category": kwargs.pop("role_category", "software_engineer"),
        "description": description,
        "remote_type": kwargs.pop("remote_type", "remote_worldwide"),
        "experience_min": kwargs.pop("experience_min", 1),
        "employment_type": "full_time",
        "job_url": f"https://{company.normalized_domain}/jobs/1",
        "status": JobStatus.ACTIVE,
        "enrichment_status": "enriched",
    }
    values.update(kwargs)
    return JobRepository(db_session).create_job(Job(**values))


def test_scoring_prioritizes_worldwide_and_hard_filters(db_session):
    profile = _profile(db_session)
    worldwide = _job(db_session, "Software Engineer", "Remote worldwide.")
    unclear = _job(db_session, "Software Engineer", "Remote role.", remote_type="remote_country")
    senior = _job(db_session, "Senior AI Engineer", "Remote worldwide.", role_category="ai_engineer", experience_min=6)
    onsite = _job(db_session, "Junior AI Engineer", "Onsite role.", role_category="ai_engineer", remote_type="onsite", experience_min=1)
    sales = _job(db_session, "Sales Engineer", "Remote worldwide.", role_category="sales", experience_min=1)
    service = JobMatchingService(db_session)

    matches = {job.id: service.score_job(profile.id, job.id)[0] for job in [worldwide, unclear, senior, onsite, sales]}

    assert matches[worldwide.id].total_score > matches[unclear.id].total_score
    assert matches[unclear.id].match_tier in {"worth_checking", "stretch"}
    assert matches[senior.id].eligibility_status == "unsuitable"
    assert matches[onsite.id].eligibility_status == "unsuitable"
    assert matches[sales.id].eligibility_status == "unsuitable"
