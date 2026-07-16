import pytest
from pydantic import ValidationError

from app.schemas.application_prep import ApplicationPrepListItem, ApplicationPrepRequest, ApplicationPrepResponse


def test_application_prep_request_defaults_and_rejects_user_profile_id():
    request = ApplicationPrepRequest()

    assert request.update_decision is True
    assert request.include_cold_dm_angle is True
    assert request.include_resume_focus is True
    assert request.include_checklist is True

    with pytest.raises(ValidationError):
        ApplicationPrepRequest(user_profile_id="profile-1")


def test_application_prep_response_shape():
    item = ApplicationPrepListItem(label="Concern", value="Salary not listed.", reason="Missing salary.")
    response = ApplicationPrepResponse(
        job_id="job-1",
        title="ML Engineer",
        fit_summary="Strong fit.",
        resume_focus_points=[item],
        project_talking_points=[item],
        concerns=[item],
        missing_information=["salary"],
        suggested_next_action="Tailor resume and apply today.",
        application_checklist=[item],
        generated_at="2026-07-16T00:00:00Z",
    )

    assert response.job_id == "job-1"
    assert response.concerns[0].value == "Salary not listed."
