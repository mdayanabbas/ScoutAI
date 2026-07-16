from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationPacketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    update_decision: bool = True
    include_resume_bullets: bool = True
    include_cover_note_outline: bool = True
    include_cold_dm_outline: bool = True
    include_checklist: bool = True
    include_risk_review: bool = True


class ApplicationPacketItem(BaseModel):
    label: str
    value: str
    reason: str


class ApplicationPacketSection(BaseModel):
    title: str
    items: list[ApplicationPacketItem]


class ApplicationPacketResponse(BaseModel):
    job_id: str
    decision_id: str | None = None
    company_name: str | None = None
    title: str
    role_category: str | None = None
    match_tier: str | None = None
    total_score: float | None = None
    remote_eligibility: str | None = None
    application_positioning: str
    resume_focus: list[ApplicationPacketItem]
    resume_bullet_suggestions: list[ApplicationPacketItem]
    project_evidence_to_use: list[ApplicationPacketItem]
    cover_note_outline: ApplicationPacketSection | None = None
    cold_dm_outline: ApplicationPacketSection | None = None
    application_checklist: list[ApplicationPacketItem]
    risks_to_verify: list[ApplicationPacketItem]
    suggested_apply_plan: list[ApplicationPacketItem]
    generated_at: datetime
