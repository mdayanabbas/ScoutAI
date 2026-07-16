from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.enums import JobApplicationDecisionStatus


class JobApplicationDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: JobApplicationDecisionStatus = JobApplicationDecisionStatus.INTERESTED
    decision_status: JobApplicationDecisionStatus | None = None
    priority: str | None = Field(default=None, max_length=16)
    notes: str | None = Field(default=None, max_length=5000)
    next_action: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def use_decision_status_alias(self):
        if self.decision_status is not None:
            self.status = self.decision_status
        return self


class JobApplicationDecisionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: JobApplicationDecisionStatus | None = None
    decision_status: JobApplicationDecisionStatus | None = None
    priority: str | None = Field(default=None, max_length=16)
    notes: str | None = Field(default=None, max_length=5000)
    fit_summary: str | None = Field(default=None, max_length=2000)
    concerns: list[str] | None = None
    next_action: str | None = Field(default=None, max_length=1000)
    next_action_due_at: datetime | None = None

    @model_validator(mode="after")
    def use_decision_status_alias(self):
        if self.decision_status is not None:
            self.status = self.decision_status
        return self


class JobApplicationDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    user_profile_id: str
    status: str
    decision_status: str
    priority: str | None = None
    notes: str | None = None
    fit_summary: str | None = None
    concerns: list[str] | None = None
    next_action: str | None = None
    next_action_due_at: datetime | None = None
    source_snapshot: dict | None = None
    match_snapshot: dict | None = None
    decided_at: datetime | None = None
    saved_at: datetime | None = None
    applied_at: datetime | None = None
    skipped_at: datetime | None = None
    archived_at: datetime | None = None
    last_status_changed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class JobApplicationDecisionListItemRead(JobApplicationDecisionRead):
    job_title: str | None = None
    company_id: str | None = None


class JobApplicationDecisionListRead(BaseModel):
    items: list[JobApplicationDecisionListItemRead]
    total: int
    limit: int
    offset: int


class JobApplicationDecisionStatusCountsRead(BaseModel):
    saved: int = 0
    interested: int = 0
    applied: int = 0
    skipped: int = 0
    not_interested: int = 0
    needs_custom_resume: int = 0
    needs_cold_dm: int = 0
    interviewing: int = 0
    rejected: int = 0
    offer: int = 0
    dismissed: int = 0
    archived: int = 0
    total: int = 0
