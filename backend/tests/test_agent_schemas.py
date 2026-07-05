from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    AgentRunCreate,
    AgentRunRead,
    AgentRunUpdate,
    AgentStepCreate,
    AgentStepRead,
    AgentStepUpdate,
)


class AgentRunObj:
    id = "agent-run-1"
    company_id = "company-1"
    job_id = None
    agent_name = "company_research"
    status = "pending"
    model_provider = None
    model_name = None
    input_summary = None
    output_summary = None
    error_message = None
    latency_ms = None
    started_at = None
    finished_at = None
    metadata = {"trace": "1"}
    created_at = datetime.now(timezone.utc)
    updated_at = None


class AgentStepObj:
    id = "step-1"
    agent_run_id = "agent-run-1"
    step_name = "parse"
    step_order = 1
    input_payload = {"a": 1}
    output_payload = {"b": 2}
    error_message = None
    latency_ms = 5
    created_at = datetime.now(timezone.utc)
    updated_at = None


def test_agent_run_create_requires_agent_name():
    with pytest.raises(ValidationError):
        AgentRunCreate()


def test_agent_run_update_allows_partial_update():
    assert AgentRunUpdate(output_summary="ok").output_summary == "ok"


def test_agent_run_read_supports_from_attributes():
    assert AgentRunRead.model_validate(AgentRunObj()).metadata == {"trace": "1"}


def test_agent_step_create_requires_name_and_order():
    with pytest.raises(ValidationError):
        AgentStepCreate(step_name="parse")


def test_agent_step_update_allows_partial_update():
    assert AgentStepUpdate(error_message="failed").error_message == "failed"


def test_agent_step_read_supports_from_attributes():
    assert AgentStepRead.model_validate(AgentStepObj()).output_payload == {"b": 2}
