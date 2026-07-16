from app.models.job_application_decision import JobApplicationDecision

from job_application_decision_helpers import create_job, create_user_profile


def test_job_application_decision_model_persists(db_session):
    user = create_user_profile(db_session)
    job = create_job(db_session)

    decision = JobApplicationDecision(
        job_id=job.id,
        user_profile_id=user.id,
        status="interested",
        notes="Worth applying.",
    )
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)

    assert decision.id
    assert decision.job_id == job.id
    assert decision.user_profile_id == user.id
    assert decision.status == "interested"
    assert decision.notes == "Worth applying."
