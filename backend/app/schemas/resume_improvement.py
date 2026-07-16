from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeImprovementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    update_decision: bool = True
    include_section_suggestions: bool = True
    include_bullet_suggestions: bool = True
    include_skill_gap_suggestions: bool = True
    include_project_reordering: bool = True
    include_remote_fit_suggestions: bool = True


class ResumeImprovementItem(BaseModel):
    category: str
    suggestion: str
    reason: str
    priority: str
    evidence: str | None = None
    caution: str | None = None


class ResumeSectionSuggestion(BaseModel):
    section: str
    action: str
    suggestion: str
    reason: str
    priority: str


class ResumeBulletSuggestion(BaseModel):
    target_section: str
    bullet_template: str
    supported_by_resume: bool
    supporting_evidence: str | None = None
    caution: str | None = None


class ResumeSkillGapSuggestion(BaseModel):
    skill: str
    found_in_resume: bool
    required_or_preferred: str
    suggestion: str
    caution: str | None = None


class ResumeImprovementResponse(BaseModel):
    job_id: str
    decision_id: str | None = None
    resume_id: str | None = None
    resume_used: bool = False
    company_name: str | None = None
    title: str
    match_tier: str | None = None
    total_score: float | None = None
    remote_eligibility: str | None = None
    improvement_summary: str
    section_suggestions: list[ResumeSectionSuggestion] = Field(default_factory=list)
    bullet_suggestions: list[ResumeBulletSuggestion] = Field(default_factory=list)
    skill_gap_suggestions: list[ResumeSkillGapSuggestion] = Field(default_factory=list)
    project_reordering_suggestions: list[ResumeImprovementItem] = Field(default_factory=list)
    remote_fit_suggestions: list[ResumeImprovementItem] = Field(default_factory=list)
    risks: list[ResumeImprovementItem] = Field(default_factory=list)
    suggested_next_action: str
    generated_at: datetime
