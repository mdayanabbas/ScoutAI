from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.company_watchlist import (
    CompanyWatchlistCreate,
    CompanyWatchlistFromJobRequest,
    CompanyWatchlistJobsResponse,
    CompanyWatchlistListResponse,
    CompanyWatchlistResponse,
    CompanyWatchlistStatsResponse,
    CompanyWatchlistUpdate,
)
from app.services.company_watchlist_service import CompanyWatchlistService

router = APIRouter(prefix="/company-watchlist", tags=["company-watchlist"])


def get_company_watchlist_service(db: Session = Depends(get_db)) -> CompanyWatchlistService:
    return CompanyWatchlistService(db)


@router.post("", response_model=CompanyWatchlistResponse, status_code=status.HTTP_201_CREATED)
def create_company_watchlist_item(
    data: CompanyWatchlistCreate,
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    return service.create_watchlist_item(data)


@router.get("", response_model=CompanyWatchlistListResponse)
def list_company_watchlist_items(
    watch_status: str | None = None,
    priority: str | None = None,
    remote_interest: str | None = None,
    junior_friendliness_signal: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    has_recommended_jobs: bool | None = None,
    has_recent_jobs: bool | None = None,
    include_archived: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    return service.list_watchlist_items(
        watch_status=watch_status,
        priority=priority,
        remote_interest=remote_interest,
        junior_friendliness_signal=junior_friendliness_signal,
        tag=tag,
        search=search,
        has_recommended_jobs=has_recommended_jobs,
        has_recent_jobs=has_recent_jobs,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=CompanyWatchlistStatsResponse)
def get_company_watchlist_stats(
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    return service.get_stats()


@router.post("/from-job/{job_id}", response_model=CompanyWatchlistResponse, status_code=status.HTTP_201_CREATED)
def watch_company_from_job(
    job_id: str,
    data: CompanyWatchlistFromJobRequest | None = None,
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    payload = None
    if data is not None:
        payload = CompanyWatchlistCreate(company_name=data.company_name or "from job", **data.model_dump(exclude={"company_name"}))
    return service.watch_company_from_job(job_id, payload)


@router.get("/{item_id}", response_model=CompanyWatchlistResponse)
def get_company_watchlist_item(
    item_id: str,
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    return service.get_watchlist_item(item_id)


@router.patch("/{item_id}", response_model=CompanyWatchlistResponse)
def update_company_watchlist_item(
    item_id: str,
    data: CompanyWatchlistUpdate,
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    return service.update_watchlist_item(item_id, data)


@router.post("/{item_id}/archive", response_model=CompanyWatchlistResponse)
def archive_company_watchlist_item(
    item_id: str,
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    return service.archive_watchlist_item(item_id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_watchlist_item(
    item_id: str,
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    service.delete_watchlist_item(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{item_id}/jobs", response_model=CompanyWatchlistJobsResponse)
def list_company_watchlist_jobs(
    item_id: str,
    recommended_only: bool = False,
    active_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: CompanyWatchlistService = Depends(get_company_watchlist_service),
):
    return service.list_jobs_for_item(
        item_id,
        recommended_only=recommended_only,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )
