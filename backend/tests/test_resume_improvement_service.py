from datetime import datetime, timezone

from app.models.job_application_decision import JobApplicationDecision
from app.models.job_match import JobMatch
from app.models.job_matching_profile import JobMatchingProfile
from app.models.resume import Resume
from app.repositories.job_application_decision_repository import JobApplicationDecisionRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.schemas.resume_improvement import ResumeImprovementRequest
from app.services.resume_improvement_service import ResumeImprovementService

from job_application_decision_helpers import create_job, create_user_profile


def _profile(db_session, user_id: str):
    profile = JobMatchingProfile(
        user_profile_id=user_id,
        target_titles_json=["AI Engineer"],
        target_role_categories_json=["ai_engineer"],
        preferred_seniority_json=["entry_level"],
        years_of_experience=1,
        skills_json=[{"name": "Python"}, {"name": "Docker"}],
        technologies_json=[{"name": "FastAPI"}, {"name": "PostgreSQL"}, {"name": "LLMs"}],
        accepted_employment_types_json=["full_time"],
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def _match(db_session, profile, job, *, tier="best_match"):
    return JobMatchRepository(db_session).create(
        JobMatch(
            job_id=job.id,
            job_matching_profile_id=profile.id,
            eligibility_status="eligible",
            eligibility_reason="Strong match",
            remote_eligibility="work_from_anywhere",
            match_tier=tier,
            total_score=92,
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
            positive_signals_json=["python"],
            negative_signals_json=[],
            missing_information_json=[],
            score_breakdown_json={},
            scoring_version="job-match-v1.1",
            scored_at=datetime.now(timezone.utc),
        )
    )


def _resume(db_session, user_id: str):
    return ResumeRepository(db_session).create(
        Resume(
            user_profile_id=user_id,
            filename="safe.txt",
            original_filename="resume.txt",
            content_type="text/plain",
            file_size_bytes=10,
            file_sha256="b" * 64,
            storage_path="/tmp/safe.txt",
            is_active=True,
            parse_status="parsed",
            raw_text="Built Python FastAPI systems.",
            parsed_summary_json={"text": "AI backend work"},
            skills_json=["Python"],
            technologies_json=["FastAPI"],
            projects_json=[{"title": "ScoutAI", "text": "Python FastAPI job matching"}],
            experience_json=[],
            education_json=[],
            certifications_json=[],
            links_json=[],
            parsed_at=datetime.now(timezone.utc),
        )
    )


def _job_with_requirements(db_session):
    job = create_job(db_session, title="AI Engineer")
    return JobRepository(db_session).update_job(
        job,
        {
            "required_skills_json": ["Python", "Docker"],
            "preferred_skills_json": ["FastAPI"],
            "technologies_json": ["PostgreSQL"],
            "description": "Remote worldwide role building LLM workflows.",
            "work_authorization": None,
        },
    )


def test_service_generates_resume_aware_suggestions_and_creates_decision(db_session):
    user = create_user_profile(db_session)
    profile = _profile(db_session, user.id)
    job = _job_with_requirements(db_session)
    _match(db_session, profile, job)
    resume = _resume(db_session, user.id)

    response = ResumeImprovementService(db_session).generate_for_job(job.id, ResumeImprovementRequest())
    decision = JobApplicationDecisionRepository(db_session).get_by_job_and_user_profile(job.id, user.id)
    text = response.model_dump_json()

    assert response.resume_used is True
    assert response.resume_id == resume.id
    assert response.decision_id == decision.id
    assert decision.status == "needs_custom_resume"
    assert any(item.found_in_resume and item.skill == "Python" for item in response.skill_gap_suggestions)
    assert any((not item.found_in_resume) and item.skill == "Docker" for item in response.skill_gap_suggestions)
    assert response.section_suggestions
    assert response.bullet_suggestions
    assert any("[project name]" in item.bullet_template for item in response.bullet_suggestions)
    assert "increased revenue" not in text
    assert "Built Python FastAPI systems" not in text
    assert "/tmp/safe.txt" not in text
    assert any("ScoutAI" in item.suggestion or item.evidence == "ScoutAI" for item in response.project_reordering_suggestions)
    assert response.remote_fit_suggestions


def test_service_handles_no_active_resume_gracefully(db_session):
    user = create_user_profile(db_session)
    profile = _profile(db_session, user.id)
    job = _job_with_requirements(db_session)
    _match(db_session, profile, job)

    response = ResumeImprovementService(db_session).generate_for_job(
        job.id,
        ResumeImprovementRequest(update_decision=False),
    )

    assert response.resume_used is False
    assert "No active resume" in response.improvement_summary
    assert response.bullet_suggestions
    assert any(item.caution for item in response.bullet_suggestions)
    assert response.suggested_next_action == "Upload an active resume before generating final application materials."


def test_service_preserves_applied_status_notes_and_does_not_mutate_job_or_match(db_session):
    user = create_user_profile(db_session)
    profile = _profile(db_session, user.id)
    job = _job_with_requirements(db_session)
    original_title = job.title
    match = _match(db_session, profile, job)
    _resume(db_session, user.id)
    decision = JobApplicationDecisionRepository(db_session).create(
        JobApplicationDecision(
            job_id=job.id,
            user_profile_id=user.id,
            status="applied",
            notes="Keep my note",
            applied_at=datetime.now(timezone.utc),
        )
    )

    ResumeImprovementService(db_session).generate_for_decision(decision.id, ResumeImprovementRequest())
    updated = JobApplicationDecisionRepository(db_session).get_by_id(decision.id)
    db_session.refresh(job)
    db_session.refresh(match)

    assert updated.status == "applied"
    assert updated.notes == "Keep my note"
    assert updated.applied_at is not None
    assert job.title == original_title
    assert match.total_score == 92
