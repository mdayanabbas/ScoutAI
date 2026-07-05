from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def map_metadata_json(cls, value: Any) -> Any:
        if isinstance(value, dict):
            if "metadata" not in value and "metadata_json" in value:
                value["metadata"] = value["metadata_json"]
            return value

        if hasattr(value, "metadata_json"):
            return {
                "id": value.id,
                "company_id": value.company_id,
                "job_id": value.job_id,
                "agent_name": value.agent_name,
                "status": value.status,
                "model_provider": value.model_provider,
                "model_name": value.model_name,
                "input_summary": value.input_summary,
                "output_summary": value.output_summary,
                "error_message": value.error_message,
                "latency_ms": value.latency_ms,
                "started_at": value.started_at,
                "finished_at": value.finished_at,
                "metadata": value.metadata_json,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        return value


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


class AgentRunMarkSuccessRequest(BaseModel):
    output_summary: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)


class AgentRunMarkFailedRequest(BaseModel):
    error_message: str = Field(min_length=1)
    latency_ms: int | None = Field(default=None, ge=0)
