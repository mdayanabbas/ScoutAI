from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.enums import AgentRunStatus


class AgentRunCreate(BaseModel):
    company_id: str | None = None
    job_id: str | None = None
    agent_name: str
    status: AgentRunStatus = AgentRunStatus.PENDING
    model_provider: str | None = None
    model_name: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error_message: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class AgentRunUpdate(BaseModel):
    company_id: str | None = None
    job_id: str | None = None
    agent_name: str | None = None
    status: AgentRunStatus | None = None
    model_provider: str | None = None
    model_name: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error_message: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str | None = None
    job_id: str | None = None
    agent_name: str
    status: AgentRunStatus
    model_provider: str | None = None
    model_name: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("metadata", mode="before")
    @classmethod
    def ignore_non_dict_metadata(cls, value: Any) -> dict[str, Any] | None:
        return value if isinstance(value, dict) or value is None else None


class AgentRunListItem(AgentRunRead):
    pass


class AgentStepCreate(BaseModel):
    step_name: str
    step_order: int
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    error_message: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)


class AgentStepUpdate(BaseModel):
    step_name: str | None = None
    step_order: int | None = None
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    error_message: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)


class AgentStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_run_id: str
    step_name: str
    step_order: int | None = None
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
