from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationPrepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    update_decision: bool = True
    include_cold_dm_angle: bool = True
    include_resume_focus: bool = True
    include_checklist: bool = True


class ApplicationPrepListItem(BaseModel):
    label: str
    value: str
    reason: str


class ApplicationPrepResponse(BaseModel):
    job_id: str
    decision_id: str | None = None
    company_name: str | None = None
    title: str
    match_tier: str | None = None
    total_score: float | None = None
    remote_eligibility: str | None = None
    fit_summary: str
    resume_focus_points: list[ApplicationPrepListItem]
    project_talking_points: list[ApplicationPrepListItem]
    concerns: list[ApplicationPrepListItem]
    missing_information: list[str]
    suggested_next_action: str
    cold_dm_angle: str | None = None
    application_checklist: list[ApplicationPrepListItem]
    generated_at: datetime
