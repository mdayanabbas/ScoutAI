from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.discovery import (
    DiscoveryCandidateRead,
    DiscoveryRunRead,
    DiscoveryRunResult,
    ManualDiscoveryRequest,
)
from app.schemas.himalayas_discovery import (
    HimalayasDiscoveryRequest,
    HimalayasDiscoveryResult,
    HimalayasQueryPlanRead,
)
from app.schemas.we_work_remotely_discovery import (
    WWRDiscoveryRequest,
    WWRDiscoveryResult,
    WWRFeedPlanRead,
)
from app.schemas.remotive_discovery import (
    RemotiveDiscoveryRequest,
    RemotiveDiscoveryResult,
    RemotiveQueryPlanRead,
)
from app.schemas.remote_discovery import (
    RemoteJobDiscoveryOrchestratorResult,
    RemoteJobDiscoveryPlanRead,
    RemoteJobDiscoveryRunRequest,
)
from app.discovery.sources.hacker_news.schemas import (
    HackerNewsDiscoveryRequest,
    HackerNewsDiscoveryResponse,
)
from app.services.discovery_service import DiscoveryService
from app.services.himalayas_remote_job_discovery_service import (
    HimalayasRemoteJobDiscoveryService,
)
from app.services.we_work_remotely_discovery_service import (
    WeWorkRemotelyDiscoveryService,
)
from app.services.remotive_remote_job_discovery_service import (
    RemotiveRemoteJobDiscoveryService,
)
from app.services.remote_job_discovery_orchestrator_service import (
    RemoteJobDiscoveryOrchestratorService,
)
from app.utils.enums import DiscoveryRunStatus, DiscoverySource

router = APIRouter(prefix="/discovery", tags=["discovery"])


def get_discovery_service(db: Session = Depends(get_db)) -> DiscoveryService:
    return DiscoveryService(db)


def get_himalayas_service(db: Session = Depends(get_db)) -> HimalayasRemoteJobDiscoveryService:
    return HimalayasRemoteJobDiscoveryService(db)


def get_we_work_remotely_service(db: Session = Depends(get_db)) -> WeWorkRemotelyDiscoveryService:
    return WeWorkRemotelyDiscoveryService(db)


def get_remotive_service(db: Session = Depends(get_db)) -> RemotiveRemoteJobDiscoveryService:
    return RemotiveRemoteJobDiscoveryService(db)


def get_remote_discovery_orchestrator_service(db: Session = Depends(get_db)) -> RemoteJobDiscoveryOrchestratorService:
    return RemoteJobDiscoveryOrchestratorService(db)


@router.post(
    "/manual",
    response_model=DiscoveryRunResult,
    status_code=status.HTTP_201_CREATED,
    summary="Run manual startup discovery",
)
async def run_manual_discovery(
    data: ManualDiscoveryRequest,
    service: DiscoveryService = Depends(get_discovery_service),
):
    return await service.run_manual_discovery(data)


@router.post(
    "/hacker-news",
    response_model=HackerNewsDiscoveryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Hacker News startup discovery",
)
async def run_hacker_news_discovery(
    data: HackerNewsDiscoveryRequest,
    service: DiscoveryService = Depends(get_discovery_service),
):
    result = await service.run_hacker_news_discovery(data)
    if (
        result.run.status == DiscoveryRunStatus.FAILED
        and result.run.candidates_found == 0
        and result.run.error_message != "No candidates were successfully processed"
    ):
        raise AppError(
            code="HACKER_NEWS_DISCOVERY_ERROR",
            message="Hacker News discovery failed",
            status_code=502,
            details={"run_id": result.run.id},
        )
    return result


@router.get(
    "/himalayas/jobs/query-plan",
    response_model=HimalayasQueryPlanRead,
    summary="Preview targeted Himalayas remote-job queries",
)
def preview_himalayas_job_queries(
    service: HimalayasRemoteJobDiscoveryService = Depends(get_himalayas_service),
):
    return service.query_plan_result()


@router.post(
    "/himalayas/jobs",
    response_model=HimalayasDiscoveryResult,
    summary="Run targeted Himalayas remote-job discovery",
)
async def run_himalayas_job_discovery(
    data: HimalayasDiscoveryRequest | None = None,
    service: HimalayasRemoteJobDiscoveryService = Depends(get_himalayas_service),
):
    request = data or HimalayasDiscoveryRequest()
    return await service.run_discovery(
        force=request.force,
        max_queries=request.max_queries,
        max_pages_per_query=request.max_pages_per_query,
        score_after_ingestion=request.score_after_ingestion,
    )


@router.get(
    "/we-work-remotely/jobs/feed-plan",
    response_model=WWRFeedPlanRead,
    summary="Preview targeted We Work Remotely RSS feeds",
)
def preview_we_work_remotely_feed_plan(
    include_all_other: bool | None = None,
    service: WeWorkRemotelyDiscoveryService = Depends(get_we_work_remotely_service),
):
    return service.feed_plan_result(include_all_other=include_all_other)


@router.post(
    "/we-work-remotely/jobs",
    response_model=WWRDiscoveryResult,
    summary="Run targeted We Work Remotely RSS job discovery",
)
async def run_we_work_remotely_job_discovery(
    data: WWRDiscoveryRequest | None = None,
    service: WeWorkRemotelyDiscoveryService = Depends(get_we_work_remotely_service),
):
    request = data or WWRDiscoveryRequest()
    return await service.run_discovery(
        force=request.force,
        include_all_other=request.include_all_other,
        max_items_per_feed=request.max_items_per_feed,
        score_after_ingestion=request.score_after_ingestion,
    )


@router.get(
    "/remotive/jobs/query-plan",
    response_model=RemotiveQueryPlanRead,
    summary="Preview targeted Remotive remote-job requests",
)
def preview_remotive_job_queries(
    max_requests: int | None = Query(default=None, ge=1, le=10),
    limit_per_request: int | None = Query(default=None, ge=1, le=500),
    service: RemotiveRemoteJobDiscoveryService = Depends(get_remotive_service),
):
    return service.query_plan_result(max_requests=max_requests, limit_per_request=limit_per_request)


@router.post(
    "/remotive/jobs",
    response_model=RemotiveDiscoveryResult,
    summary="Run targeted Remotive remote-job discovery",
)
async def run_remotive_job_discovery(
    data: RemotiveDiscoveryRequest | None = None,
    service: RemotiveRemoteJobDiscoveryService = Depends(get_remotive_service),
):
    request = data or RemotiveDiscoveryRequest()
    return await service.run_discovery(
        force=request.force,
        max_requests=request.max_requests,
        limit_per_request=request.limit_per_request,
        score_after_ingestion=request.score_after_ingestion,
    )


@router.get(
    "/remote-jobs/plan",
    response_model=RemoteJobDiscoveryPlanRead,
    summary="Preview unified remote-job discovery plan",
)
def preview_remote_job_discovery_plan(
    service: RemoteJobDiscoveryOrchestratorService = Depends(get_remote_discovery_orchestrator_service),
):
    return service.plan_remote_discovery()


@router.post(
    "/remote-jobs/run",
    response_model=RemoteJobDiscoveryOrchestratorResult,
    summary="Run unified remote-job discovery",
)
async def run_remote_job_discovery(
    data: RemoteJobDiscoveryRunRequest | None = None,
    service: RemoteJobDiscoveryOrchestratorService = Depends(get_remote_discovery_orchestrator_service),
):
    request = data or RemoteJobDiscoveryRunRequest()
    return await service.run_remote_discovery(
        force=request.force,
        sources=request.sources,
        score_after_ingestion=request.score_after_ingestion,
        himalayas_options=request.himalayas.model_dump(exclude_none=True) if request.himalayas else None,
        we_work_remotely_options=request.we_work_remotely.model_dump(exclude_none=True) if request.we_work_remotely else None,
        remotive_options=request.remotive.model_dump(exclude_none=True) if request.remotive else None,
    )


@router.get(
    "/runs",
    response_model=PaginatedResponse[DiscoveryRunRead],
    summary="List discovery runs",
)
def list_discovery_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source: DiscoverySource | None = None,
    status: DiscoveryRunStatus | None = None,
    service: DiscoveryService = Depends(get_discovery_service),
):
    offset = (page - 1) * page_size
    items = service.list_runs(
        offset=offset,
        limit=page_size,
        source=source,
        status=status,
    )
    total = service.count_runs(source=source, status=status)
    return PaginatedResponse[DiscoveryRunRead](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + len(items) < total,
        has_prev=page > 1,
    )


@router.get(
    "/runs/{run_id}",
    response_model=DiscoveryRunResult,
    summary="Get discovery run",
)
def get_discovery_run(
    run_id: str,
    service: DiscoveryService = Depends(get_discovery_service),
):
    return service.get_run_result(run_id)


@router.get(
    "/candidates/{candidate_id}",
    response_model=DiscoveryCandidateRead,
    summary="Get discovery candidate",
)
def get_discovery_candidate(
    candidate_id: str,
    service: DiscoveryService = Depends(get_discovery_service),
):
    return service.get_candidate(candidate_id)
