from datetime import datetime, timezone

from app.models.job_application_decision import JobApplicationDecision
from app.models.job_match import JobMatch
from app.models.job_matching_profile import JobMatchingProfile
from app.repositories.job_application_decision_repository import JobApplicationDecisionRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_repository import JobRepository
from app.schemas.application_prep import ApplicationPrepRequest
from app.services.application_prep_service import ApplicationPrepService

from job_application_decision_helpers import create_job, create_user_profile


def _profile(db_session, *, skills=None, technologies=None):
    user = create_user_profile(db_session)
    profile = JobMatchingProfile(
        user_profile_id=user.id,
        target_titles_json=["AI Engineer", "Software Engineer"],
        target_role_categories_json=["ai_engineer", "software_engineer"],
        preferred_seniority_json=["entry_level", "junior"],
        years_of_experience=1,
        skills_json=skills or [{"name": "Python"}, {"name": "Machine Learning"}, {"name": "Backend Development"}],
        technologies_json=technologies or [{"name": "FastAPI"}, {"name": "PostgreSQL"}, {"name": "Docker"}, {"name": "LLMs"}],
        accepted_employment_types_json=["full_time", "internship"],
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return user, profile


def _match(db_session, profile, job, *, tier="best_match", remote="work_from_anywhere", missing=None, score=91):
    return JobMatchRepository(db_session).create(
        JobMatch(
            job_id=job.id,
            job_matching_profile_id=profile.id,
            eligibility_status="eligible",
            eligibility_reason="Strong match",
            remote_eligibility=remote,
            match_tier=tier,
            total_score=score,
            role_score=95,
            seniority_score=90,
            remote_score=100,
            experience_score=95,
            employment_type_score=90,
            skills_score=90,
            technology_score=90,
            salary_score=60,
            company_score=60,
            confidence_score=90,
            hard_filter_reasons_json=[],
            positive_signals_json=["python", "machine learning"],
            negative_signals_json=[],
            missing_information_json=missing or [],
            score_breakdown_json={},
            scoring_version="job-match-v1.1",
            scored_at=datetime.now(timezone.utc),
        )
    )


def test_generates_ml_best_match_and_creates_decision(db_session):
    _user, profile = _profile(db_session)
    job = create_job(db_session, title="Machine Learning Engineer Intern")
    JobRepository(db_session).update_job(
        job,
        {
            "role_category": "ml_engineer",
            "required_skills_json": ["Python", "Machine Learning"],
            "technologies_json": ["LLMs", "FastAPI"],
            "description": "Build production ML and LLM workflows. Remote worldwide.",
            "experience_min": 0,
            "salary_min": None,
            "salary_max": None,
        },
    )
    _match(db_session, profile, job, tier="best_match")

    result = ApplicationPrepService(db_session).generate_for_job(job.id, ApplicationPrepRequest())
    decision = JobApplicationDecisionRepository(db_session).get_by_job_and_user_profile(job.id, profile.user_profile_id)

    assert result.match_tier == "best_match"
    assert result.fit_summary.startswith("Strong fit")
    assert any("Python" in item.value for item in result.resume_focus_points)
    assert any("Salary not listed" in item.value for item in result.concerns)
    assert decision.status == "needs_custom_resume"
    assert decision.priority == "high"
    assert decision.fit_summary == result.fit_summary


def test_generates_swe_fit_and_safe_project_points(db_session):
    _user, profile = _profile(db_session)
    job = create_job(db_session, title="Software Engineer")
    JobRepository(db_session).update_job(
        job,
        {
            "role_category": "software_engineer",
            "required_skills_json": ["Python"],
            "technologies_json": ["PostgreSQL", "Docker"],
            "experience_min": 2,
            "employment_type": "full_time",
        },
    )
    _match(db_session, profile, job, tier="strong_match")

    result = ApplicationPrepService(db_session).generate_for_job(job.id, ApplicationPrepRequest(update_decision=False))

    assert result.fit_summary.startswith("Good fit")
    assert any("backend APIs" in item.value for item in result.project_talking_points)
    assert not any("React" in item.value for item in result.resume_focus_points)


def test_stretch_creates_saved_decision_and_unclear_remote_concern(db_session):
    _user, profile = _profile(db_session)
    job = create_job(db_session, title="AI Engineer")
    JobRepository(db_session).update_job(job, {"required_skills_json": ["Python"], "apply_url": None, "job_url": None})
    _match(db_session, profile, job, tier="stretch", remote="remote_eligibility_unclear")

    result = ApplicationPrepService(db_session).generate_for_job(job.id, ApplicationPrepRequest())
    decision = JobApplicationDecisionRepository(db_session).get_by_job_and_user_profile(job.id, profile.user_profile_id)

    assert decision.status == "saved"
    assert decision.priority == "low"
    assert any("Remote eligibility needs verification" in item.value for item in result.concerns)
    assert any("Apply URL is missing" in item.value for item in result.concerns)
    assert any("Apply through source link" in item.value for item in result.application_checklist)


def test_updates_existing_decision_without_overwriting_notes_or_applied_status(db_session):
    user, profile = _profile(db_session)
    job = create_job(db_session)
    _match(db_session, profile, job, tier="best_match")
    decision = JobApplicationDecisionRepository(db_session).create(
        JobApplicationDecision(
            job_id=job.id,
            user_profile_id=user.id,
            status="applied",
            priority="urgent",
            notes="Already sent application.",
            applied_at=datetime.now(timezone.utc),
        )
    )

    ApplicationPrepService(db_session).generate_for_decision(decision.id, ApplicationPrepRequest())
    updated = JobApplicationDecisionRepository(db_session).get_by_id(decision.id)

    assert updated.status == "applied"
    assert updated.priority == "urgent"
    assert updated.notes == "Already sent application."
    assert updated.fit_summary
    assert updated.next_action == "Track response and follow up later if appropriate."


def test_does_not_mutate_job_or_match_and_handles_missing_match(db_session):
    _user, _matching_profile = _profile(db_session)
    job = create_job(db_session, title="Backend Engineer")
    original_title = job.title

    result = ApplicationPrepService(db_session).generate_for_job(job.id, ApplicationPrepRequest(update_decision=False))
    db_session.refresh(job)

    assert result.match_tier is None
    assert job.title == original_title


def test_stale_match_adds_concern(db_session):
    _user, profile = _profile(db_session)
    job = create_job(db_session)
    match = _match(db_session, profile, job)
    setattr(match, "is_stale", True)

    result = ApplicationPrepService(db_session).generate_for_job(job.id, ApplicationPrepRequest(update_decision=False))

    assert any("stale" in item.value.lower() for item in result.concerns)
