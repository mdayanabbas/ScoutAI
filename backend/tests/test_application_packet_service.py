from datetime import datetime, timezone

from app.models.job_application_decision import JobApplicationDecision
from app.models.job_match import JobMatch
from app.models.job_matching_profile import JobMatchingProfile
from app.repositories.job_application_decision_repository import JobApplicationDecisionRepository
from app.repositories.job_match_repository import JobMatchRepository
from app.repositories.job_repository import JobRepository
from app.schemas.application_packet import ApplicationPacketRequest
from app.services.application_packet_service import ApplicationPacketService

from job_application_decision_helpers import create_job, create_user_profile


def _profile(db_session, *, skills=None, technologies=None):
    user = create_user_profile(db_session)
    profile = JobMatchingProfile(
        user_profile_id=user.id,
        target_titles_json=["AI Engineer", "Software Engineer", "Forward Deployed Engineer"],
        target_role_categories_json=["ai_engineer", "software_engineer", "forward_deployed_engineer"],
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


def _match(db_session, profile, job, *, tier="best_match", remote="work_from_anywhere", score=92):
    return JobMatchRepository(db_session).create(
        JobMatch(
            job_id=job.id,
            job_matching_profile_id=profile.id,
            eligibility_status="eligible" if tier != "unsuitable" else "unsuitable",
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
            missing_information_json=[],
            score_breakdown_json={},
            scoring_version="job-match-v1.1",
            scored_at=datetime.now(timezone.utc),
        )
    )


def test_generates_packet_for_ml_best_match_and_creates_decision(db_session):
    _user, profile = _profile(db_session)
    job = create_job(db_session, title="Machine Learning Engineer Intern")
    JobRepository(db_session).update_job(
        job,
        {
            "role_category": "ml_engineer",
            "required_skills_json": ["Python", "Machine Learning"],
            "technologies_json": ["LLMs", "FastAPI"],
            "description": "Build production ML and LLM workflows. Remote worldwide.",
        },
    )
    _match(db_session, profile, job, tier="best_match")

    packet = ApplicationPacketService(db_session).generate_for_job(job.id, ApplicationPacketRequest())
    decision = JobApplicationDecisionRepository(db_session).get_by_job_and_user_profile(job.id, profile.user_profile_id)

    assert "ML" in packet.application_positioning or "AI" in packet.application_positioning
    assert any("Python" in item.value for item in packet.resume_focus)
    assert any("LLM" in item.value for item in packet.resume_bullet_suggestions)
    assert packet.cover_note_outline
    assert packet.cold_dm_outline
    assert packet.application_checklist
    assert decision.status == "needs_custom_resume"
    assert decision.priority == "high"


def test_generates_packet_for_swe_and_fde_matches(db_session):
    _user, profile = _profile(db_session)
    swe = create_job(db_session, title="Software Engineer")
    fde = create_job(db_session, title="Forward Deployed Engineer")
    JobRepository(db_session).update_job(swe, {"role_category": "software_engineer", "technologies_json": ["PostgreSQL", "Docker"]})
    JobRepository(db_session).update_job(fde, {"role_category": "forward_deployed_engineer", "description": "Debug customer problems and own deployments."})
    _match(db_session, profile, swe, tier="strong_match")
    _match(db_session, profile, fde, tier="worth_checking")

    service = ApplicationPacketService(db_session)
    swe_packet = service.generate_for_job(swe.id, ApplicationPacketRequest(update_decision=False))
    fde_packet = service.generate_for_job(fde.id, ApplicationPacketRequest(update_decision=False))

    assert "backend software engineering" in swe_packet.application_positioning
    assert any("backend APIs" in item.value for item in swe_packet.project_evidence_to_use)
    assert "customer-facing engineering" in fde_packet.application_positioning
    assert any("customer" in item.value.lower() for item in fde_packet.application_checklist)


def test_packet_includes_risks_and_stale_score_without_full_description(db_session):
    _user, profile = _profile(db_session)
    job = create_job(db_session, title="AI Engineer")
    long_description = "Remote unclear. Secret full description should not be returned."
    JobRepository(db_session).update_job(
        job,
        {
            "description": long_description,
            "salary_min": None,
            "salary_max": None,
            "work_authorization": None,
            "apply_url": None,
            "job_url": "https://remotive.com/jobs/1",
        },
    )
    match = _match(db_session, profile, job, tier="stretch", remote="remote_eligibility_unclear")
    setattr(match, "is_stale", True)

    packet = ApplicationPacketService(db_session).generate_for_job(job.id, ApplicationPacketRequest(update_decision=False))
    text = packet.model_dump_json()

    assert any("Salary not listed" in item.value for item in packet.risks_to_verify)
    assert any("Remote eligibility" in item.value for item in packet.risks_to_verify)
    assert any("Third-party job board" in item.value for item in packet.risks_to_verify)
    assert any("stale" in item.value.lower() for item in packet.risks_to_verify)
    assert "Secret full description" not in text
    assert "raw_payload" not in text


def test_packet_does_not_invent_metrics_or_employment_history(db_session):
    _user, profile = _profile(db_session)
    job = create_job(db_session)
    _match(db_session, profile, job)

    packet = ApplicationPacketService(db_session).generate_for_job(job.id, ApplicationPacketRequest(update_decision=False))
    text = packet.model_dump_json()

    assert "at X company" not in text
    assert "increased revenue" not in text
    assert "[metric]" in text


def test_stretch_creates_saved_and_existing_decision_is_updated_safely(db_session):
    user, profile = _profile(db_session)
    job = create_job(db_session)
    _match(db_session, profile, job, tier="stretch")

    service = ApplicationPacketService(db_session)
    packet = service.generate_for_job(job.id, ApplicationPacketRequest())
    decision = JobApplicationDecisionRepository(db_session).get_by_job_and_user_profile(job.id, user.id)
    assert decision.status == "saved"
    assert decision.priority == "low"

    decision = JobApplicationDecisionRepository(db_session).update(
        decision,
        {"status": "applied", "priority": "urgent", "notes": "Do not overwrite", "applied_at": datetime.now(timezone.utc)},
    )
    service.generate_for_decision(decision.id, ApplicationPacketRequest())
    updated = JobApplicationDecisionRepository(db_session).get_by_id(decision.id)

    assert updated.status == "applied"
    assert updated.priority == "urgent"
    assert updated.notes == "Do not overwrite"
    assert updated.fit_summary


def test_packet_does_not_mutate_job_or_match_and_handles_missing_match_profile_fields(db_session):
    _user, _profile_obj = _profile(db_session, skills=[], technologies=[])
    job = create_job(db_session, title="Backend Engineer")
    original_title = job.title

    packet = ApplicationPacketService(db_session).generate_for_job(job.id, ApplicationPacketRequest(update_decision=False))
    db_session.refresh(job)

    assert packet.match_tier is None
    assert job.title == original_title
    assert packet.resume_focus == []
