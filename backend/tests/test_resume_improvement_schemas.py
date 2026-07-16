import pytest
from pydantic import ValidationError

from app.schemas.resume_improvement import (
    ResumeBulletSuggestion,
    ResumeImprovementRequest,
    ResumeImprovementResponse,
    ResumeSectionSuggestion,
    ResumeSkillGapSuggestion,
)


def test_resume_improvement_request_defaults_and_rejects_user_profile_id():
    request = ResumeImprovementRequest()

    assert request.update_decision is True
    assert request.include_section_suggestions is True
    assert request.include_bullet_suggestions is True
    assert request.include_skill_gap_suggestions is True
    assert request.include_project_reordering is True
    assert request.include_remote_fit_suggestions is True

    with pytest.raises(ValidationError):
        ResumeImprovementRequest(user_profile_id="profile-1")


def test_resume_improvement_response_shape():
    section = ResumeSectionSuggestion(
        section="Projects",
        action="reorder",
        suggestion="Move relevant project higher.",
        reason="Project evidence matters.",
        priority="medium",
    )
    bullet = ResumeBulletSuggestion(
        target_section="Projects",
        bullet_template="Built [project name] with Python.",
        supported_by_resume=True,
        supporting_evidence="Python",
    )
    skill = ResumeSkillGapSuggestion(
        skill="Docker",
        found_in_resume=False,
        required_or_preferred="preferred",
        suggestion="Add Docker evidence if true.",
        caution="Add only if true.",
    )
    response = ResumeImprovementResponse(
        job_id="job-1",
        title="AI Engineer",
        improvement_summary="Summary",
        section_suggestions=[section],
        bullet_suggestions=[bullet],
        skill_gap_suggestions=[skill],
        suggested_next_action="Update resume.",
        generated_at="2026-07-16T00:00:00Z",
    )

    assert response.resume_used is False
    assert response.section_suggestions[0].section == "Projects"
    assert response.bullet_suggestions[0].supported_by_resume is True
    assert response.skill_gap_suggestions[0].skill == "Docker"
