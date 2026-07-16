import pytest
from pydantic import ValidationError

from app.schemas.job_application_decision import (
    JobApplicationDecisionCreate,
    JobApplicationDecisionStatusCountsRead,
    JobApplicationDecisionUpdate,
)


def test_create_schema_defaults_and_rejects_arbitrary_user_profile_id():
    request = JobApplicationDecisionCreate()

    assert request.status == "interested"

    with pytest.raises(ValidationError):
        JobApplicationDecisionCreate(user_profile_id="profile-1")


def test_update_schema_validates_status_and_counts_shape():
    update = JobApplicationDecisionUpdate(status="applied", notes="Submitted")
    counts = JobApplicationDecisionStatusCountsRead(interested=1, applied=2, total=3)

    assert update.status == "applied"
    assert counts.applied == 2

    with pytest.raises(ValidationError):
        JobApplicationDecisionUpdate(status="maybe")
