from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import (
    AgentRunCreate,
    AgentRunListItem,
    AgentRunMarkFailedRequest,
    AgentRunMarkSuccessRequest,
    AgentRunRead,
    AgentStepCreate,
    AgentStepRead,
    AgentStepUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.agent_run_service import AgentRunService
from app.utils.enums import AgentRunStatus

router = APIRouter(tags=["agent-runs"])


def get_agent_run_service(db: Session = Depends(get_db)) -> AgentRunService:
    return AgentRunService(db)


@router.post(
    "/agent-runs",
    response_model=AgentRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create agent run",
)
def create_agent_run(
    data: AgentRunCreate,
    service: AgentRunService = Depends(get_agent_run_service),
):
    return service.create_agent_run(data)


@router.get(
    "/agent-runs",
    response_model=PaginatedResponse[AgentRunListItem],
    summary="List agent runs",
)
def list_agent_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    agent_name: str | None = None,
    status: AgentRunStatus | None = None,
    company_id: str | None = None,
    job_id: str | None = None,
    service: AgentRunService = Depends(get_agent_run_service),
):
    offset = (page - 1) * page_size
    if company_id is not None:
        items = service.list_company_runs(
            company_id,
            offset=offset,
            limit=page_size,
            agent_name=agent_name,
            status=status,
        )
    elif job_id is not None:
        items = service.list_job_runs(
            job_id,
            offset=offset,
            limit=page_size,
            agent_name=agent_name,
            status=status,
        )
    else:
        items = service.list_recent_runs(
            offset=offset,
            limit=page_size,
            agent_name=agent_name,
            status=status,
        )

    total = service.count_runs(
        agent_name=agent_name,
        status=status,
        company_id=company_id,
        job_id=job_id,
    )
    return PaginatedResponse[AgentRunListItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + len(items) < total,
        has_prev=page > 1,
    )


@router.get(
    "/agent-runs/{agent_run_id}",
    response_model=AgentRunRead,
    summary="Get agent run",
)
def get_agent_run(
    agent_run_id: str,
    service: AgentRunService = Depends(get_agent_run_service),
):
    return service.get_agent_run(agent_run_id)


@router.post(
    "/agent-runs/{agent_run_id}/mark-running",
    response_model=AgentRunRead,
    summary="Mark agent run running",
)
def mark_agent_run_running(
    agent_run_id: str,
    service: AgentRunService = Depends(get_agent_run_service),
):
    return service.mark_running(agent_run_id)


@router.post(
    "/agent-runs/{agent_run_id}/mark-success",
    response_model=AgentRunRead,
    summary="Mark agent run success",
)
def mark_agent_run_success(
    agent_run_id: str,
    data: AgentRunMarkSuccessRequest,
    service: AgentRunService = Depends(get_agent_run_service),
):
    return service.mark_success(
        agent_run_id,
        output_summary=data.output_summary,
        latency_ms=data.latency_ms,
    )


@router.post(
    "/agent-runs/{agent_run_id}/mark-failed",
    response_model=AgentRunRead,
    summary="Mark agent run failed",
)
def mark_agent_run_failed(
    agent_run_id: str,
    data: AgentRunMarkFailedRequest,
    service: AgentRunService = Depends(get_agent_run_service),
):
    return service.mark_failed(
        agent_run_id,
        error_message=data.error_message,
        latency_ms=data.latency_ms,
    )


@router.post(
    "/agent-runs/{agent_run_id}/steps",
    response_model=AgentStepRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add agent step",
)
def add_agent_step(
    agent_run_id: str,
    data: AgentStepCreate,
    service: AgentRunService = Depends(get_agent_run_service),
):
    return service.add_step(agent_run_id, data)


@router.get(
    "/agent-runs/{agent_run_id}/steps",
    response_model=list[AgentStepRead],
    summary="List agent steps",
)
def list_agent_steps(
    agent_run_id: str,
    service: AgentRunService = Depends(get_agent_run_service),
):
    return service.list_steps(agent_run_id)


@router.patch(
    "/agent-steps/{agent_step_id}",
    response_model=AgentStepRead,
    summary="Update agent step",
)
def update_agent_step(
    agent_step_id: str,
    data: AgentStepUpdate,
    service: AgentRunService = Depends(get_agent_run_service),
):
    return service.update_step(agent_step_id, data)


@router.delete(
    "/agent-steps/{agent_step_id}",
    response_model=MessageResponse,
    summary="Delete agent step",
)
def delete_agent_step(
    agent_step_id: str,
    service: AgentRunService = Depends(get_agent_run_service),
):
    service.delete_step(agent_step_id)
    return MessageResponse(message="Agent step deleted successfully")
