from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import JobApplicationDecisionStatus


class JobApplicationDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: JobApplicationDecisionStatus = JobApplicationDecisionStatus.INTERESTED
    notes: str | None = Field(default=None, max_length=5000)


class JobApplicationDecisionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: JobApplicationDecisionStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)


class JobApplicationDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    user_profile_id: str
    status: str
    notes: str | None = None
    decided_at: datetime | None = None
    archived_at: datetime | None = None
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
    interested: int = 0
    applied: int = 0
    dismissed: int = 0
    archived: int = 0
    total: int = 0
