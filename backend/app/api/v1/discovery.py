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
from app.discovery.sources.hacker_news.schemas import (
    HackerNewsDiscoveryRequest,
    HackerNewsDiscoveryResponse,
)
from app.services.discovery_service import DiscoveryService
from app.utils.enums import DiscoveryRunStatus, DiscoverySource

router = APIRouter(prefix="/discovery", tags=["discovery"])


def get_discovery_service(db: Session = Depends(get_db)) -> DiscoveryService:
    return DiscoveryService(db)


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
        and result.run.error_message != "No candidates were successfully ingested"
    ):
        raise AppError(
            code="HACKER_NEWS_DISCOVERY_ERROR",
            message="Hacker News discovery failed",
            status_code=502,
            details={"run_id": result.run.id},
        )
    return result


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
