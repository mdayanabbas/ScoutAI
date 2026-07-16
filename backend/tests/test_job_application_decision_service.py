import pytest

from app.core.errors import NotFoundError
from app.schemas.job_application_decision import JobApplicationDecisionCreate, JobApplicationDecisionUpdate
from app.services.job_application_decision_service import JobApplicationDecisionService

from job_application_decision_helpers import create_job, create_user_profile


def test_service_creates_updates_lists_counts_and_archives(db_session):
    create_user_profile(db_session)
    job = create_job(db_session)
    service = JobApplicationDecisionService(db_session)

    decision = service.create_or_update_for_job(
        job.id,
        JobApplicationDecisionCreate(status="interested", notes="Looks good"),
    )
    updated = service.update_decision(decision.id, JobApplicationDecisionUpdate(status="applied"))

    assert updated.id == decision.id
    assert updated.status == "applied"
    assert service.get_for_job(job.id).status == "applied"
    assert service.list_decisions().total == 1
    assert service.status_counts().applied == 1

    archived = service.archive_decision(decision.id)
    assert archived.status == "archived"
    assert service.list_decisions().total == 0
    assert service.status_counts().archived == 1


def test_service_unknown_job_returns_not_found(db_session):
    create_user_profile(db_session)
    service = JobApplicationDecisionService(db_session)

    with pytest.raises(NotFoundError, match="Job not found"):
        service.create_or_update_for_job("missing-job", JobApplicationDecisionCreate())
