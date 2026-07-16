import pytest
from pydantic import ValidationError

from app.schemas.application_packet import (
    ApplicationPacketItem,
    ApplicationPacketRequest,
    ApplicationPacketResponse,
    ApplicationPacketSection,
)


def test_application_packet_request_defaults_and_rejects_user_profile_id():
    request = ApplicationPacketRequest()

    assert request.update_decision is True
    assert request.include_resume_bullets is True
    assert request.include_cover_note_outline is True
    assert request.include_cold_dm_outline is True
    assert request.include_checklist is True
    assert request.include_risk_review is True

    with pytest.raises(ValidationError):
        ApplicationPacketRequest(user_profile_id="profile-1")


def test_application_packet_response_shape():
    item = ApplicationPacketItem(label="Resume focus", value="Use Python evidence.", reason="Overlap.")
    section = ApplicationPacketSection(title="Cover Note Outline", items=[item])
    response = ApplicationPacketResponse(
        job_id="job-1",
        title="ML Engineer",
        application_positioning="Position around ML.",
        resume_focus=[item],
        resume_bullet_suggestions=[item],
        project_evidence_to_use=[item],
        cover_note_outline=section,
        cold_dm_outline=section,
        application_checklist=[item],
        risks_to_verify=[item],
        suggested_apply_plan=[item],
        generated_at="2026-07-16T00:00:00Z",
    )

    assert response.job_id == "job-1"
    assert response.cover_note_outline.items[0].value == "Use Python evidence."
