from app.models.company import Company
from app.models.job import Job
from app.models.job_matching_profile import JobMatchingProfile
from app.models.user_profile import UserProfile
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository


def _setup(db_session):
    company = CompanyRepository(db_session).create_company(Company(name="Match Co", normalized_domain="match.example"))
    job = JobRepository(db_session).create_job(Job(company_id=company.id, title="Software Engineer", normalized_title="software engineer", job_url="https://match.example/jobs/1"))
    user = UserProfileRepository(db_session).create_profile(UserProfile(display_name="Abbas"))
    profile = JobMatchingProfile(user_profile_id=user.id)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return job, profile


def test_job_match_repository_upsert_updates_same_record(db_session):
    job, profile = _setup(db_session)
    repo = JobMatchRepository(db_session)
    data = {
        "eligibility_status": "eligible",
        "eligibility_reason": "Strong match.",
        "remote_eligibility": "work_from_anywhere",
        "match_tier": "best_match",
        "total_score": 90,
        "role_score": 100,
        "seniority_score": 100,
        "remote_score": 100,
        "experience_score": 100,
        "employment_type_score": 60,
        "skills_score": 60,
        "technology_score": 60,
        "salary_score": 60,
        "company_score": 60,
        "confidence_score": 80,
        "hard_filter_reasons_json": [],
        "positive_signals_json": ["software engineer"],
        "negative_signals_json": [],
        "missing_information_json": [],
        "score_breakdown_json": {},
        "scoring_version": "job-match-v1",
    }

    first, action = repo.upsert_match(profile.id, job.id, data)
    second, second_action = repo.upsert_match(profile.id, job.id, {**data, "total_score": 88})

    assert action == "created"
    assert second_action == "updated"
    assert first.id == second.id
    assert repo.get_by_profile_and_job(profile.id, job.id).total_score == 88
