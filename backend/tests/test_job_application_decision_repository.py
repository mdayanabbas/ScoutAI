from app.models.job_application_decision import JobApplicationDecision
from app.repositories.job_application_decision_repository import JobApplicationDecisionRepository

from job_application_decision_helpers import create_job, create_user_profile


def test_repository_get_list_and_status_counts(db_session):
    user = create_user_profile(db_session)
    first = create_job(db_session, title="AI Engineer")
    second = create_job(db_session, title="ML Engineer")
    repo = JobApplicationDecisionRepository(db_session)

    repo.create(JobApplicationDecision(job_id=first.id, user_profile_id=user.id, status="interested"))
    repo.create(JobApplicationDecision(job_id=second.id, user_profile_id=user.id, status="applied"))

    assert repo.get_by_job_and_user_profile(first.id, user.id).status == "interested"
    assert len(repo.list_for_user_profile(user.id)) == 2
    assert repo.count_for_user_profile(user.id) == 2
    assert repo.status_counts(user.id) == {"applied": 1, "interested": 1}


def test_repository_excludes_archived_by_default(db_session):
    user = create_user_profile(db_session)
    job = create_job(db_session)
    repo = JobApplicationDecisionRepository(db_session)

    repo.create(JobApplicationDecision(job_id=job.id, user_profile_id=user.id, status="archived"))

    assert repo.list_for_user_profile(user.id) == []
    assert repo.count_for_user_profile(user.id) == 0
    assert len(repo.list_for_user_profile(user.id, include_archived=True)) == 1
