from app.models.company import Company
from app.models.job import Job
from app.models.job_matching_profile import JobMatchingProfile
from app.models.user_profile import UserProfile
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.services.job_matching_service import JobMatchingService
from app.utils.enums import JobStatus


def _profile(db_session):
    user = UserProfileRepository(db_session).create_profile(UserProfile(display_name="Abbas"))
    profile = JobMatchingProfile(
        user_profile_id=user.id,
        target_titles_json=["AI Engineer", "Software Engineer", "SWE"],
        target_role_categories_json=["software_engineer", "ai_engineer"],
        preferred_seniority_json=["entry_level", "junior", "open"],
        years_of_experience=1,
        skills_json=[{"name": "Python"}, {"name": "Machine Learning"}, {"name": "Backend Development"}],
        technologies_json=[{"name": "FastAPI"}, {"name": "PostgreSQL"}, {"name": "Docker"}],
        accepted_employment_types_json=["full_time", "contract", "internship"],
        preferred_countries_json=["India"],
        work_authorization_countries_json=["India"],
        willing_to_relocate=False,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def _job(db_session, **kwargs):
    company = CompanyRepository(db_session).create_company(Company(name=f"Co {kwargs.get('title', 'Job')}", normalized_domain=f"{abs(hash(kwargs.get('title', 'job'))) % 10_000_000}.example"))
    values = {
        "company_id": company.id,
        "title": "Software Engineer",
        "normalized_title": "software engineer",
        "role_category": "software_engineer",
        "description": "Remote worldwide. Build APIs with Python, FastAPI and PostgreSQL.",
        "remote_type": "remote_worldwide",
        "experience_min": 1,
        "employment_type": "full_time",
        "required_skills_json": ["Python"],
        "technologies_json": ["FastAPI", "PostgreSQL"],
        "job_url": f"https://{company.normalized_domain}/jobs/1",
        "status": JobStatus.ACTIVE,
        "enrichment_status": "enriched",
    }
    values.update(kwargs)
    return JobRepository(db_session).create_job(Job(**values))


def test_service_scores_best_match_and_updates_same_record(db_session):
    profile = _profile(db_session)
    job = _job(db_session, title="AI Engineer", role_category="ai_engineer")
    service = JobMatchingService(db_session)

    match, action = service.score_job(profile.id, job.id)
    second, second_action = service.score_job(profile.id, job.id)

    assert action == "created"
    assert second_action == "updated"
    assert match.id == second.id
    assert second.eligibility_status == "eligible"
    assert second.match_tier == "best_match"
    assert second.remote_eligibility == "work_from_anywhere"
    assert second.total_score >= 85


def test_service_hard_filters_senior_onsite_and_us_citizenship(db_session):
    profile = _profile(db_session)
    job = _job(
        db_session,
        title="Senior AI Engineer",
        remote_type="onsite",
        description="Onsite in the United States. US citizenship required.",
        experience_min=5,
    )
    match, _ = JobMatchingService(db_session).score_job(profile.id, job.id)

    assert match.eligibility_status == "unsuitable"
    assert match.match_tier == "unsuitable"
    assert "onsite" in match.hard_filter_reasons_json
    assert "authorization_restriction" in match.hard_filter_reasons_json


def test_service_batch_scoring_and_stale_detection(db_session):
    profile = _profile(db_session)
    first = _job(db_session, title="SWE")
    second = _job(db_session, title="Electrical Engineer", role_category="other")
    service = JobMatchingService(db_session)

    result = service.score_jobs(profile.id, job_ids=[first.id, second.id], force=True)
    match = JobMatchRepository(db_session).get_by_profile_and_job(profile.id, first.id)
    JobRepository(db_session).update_job(first, {"description": "Remote worldwide updated."})

    assert result.jobs_scored == 2
    assert result.eligible + result.unsuitable + result.stretch + result.uncertain == 2
    assert service.is_stale(match, profile) is True
