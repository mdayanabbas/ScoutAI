from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.crawler import (
    CrawlRunListItem,
    CrawlRunMarkFailedRequest,
    CrawlRunMarkSuccessRequest,
    CrawlRunRead,
)
from app.services.crawl_run_service import CrawlRunService
from app.utils.enums import CrawlStatus

router = APIRouter(tags=["crawl-runs"])


def get_crawl_run_service(db: Session = Depends(get_db)) -> CrawlRunService:
    return CrawlRunService(db)


@router.post(
    "/companies/{company_id}/crawl-runs",
    response_model=CrawlRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create crawl run",
)
def create_crawl_run(
    company_id: str,
    service: CrawlRunService = Depends(get_crawl_run_service),
):
    return service.create_crawl_run(company_id)


@router.get(
    "/companies/{company_id}/crawl-runs",
    response_model=PaginatedResponse[CrawlRunListItem],
    summary="List company crawl runs",
)
def list_company_crawl_runs(
    company_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: CrawlRunService = Depends(get_crawl_run_service),
):
    offset = (page - 1) * page_size
    items = service.list_company_runs(company_id, offset=offset, limit=page_size)
    total = service.count_company_runs(company_id)
    return PaginatedResponse[CrawlRunListItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + len(items) < total,
        has_prev=page > 1,
    )


@router.get(
    "/crawl-runs",
    response_model=PaginatedResponse[CrawlRunListItem],
    summary="List recent crawl runs",
)
def list_recent_crawl_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: CrawlStatus | None = None,
    service: CrawlRunService = Depends(get_crawl_run_service),
):
    offset = (page - 1) * page_size
    items = service.list_recent_runs(
        offset=offset, limit=page_size, status=status
    )
    total = service.count_recent_runs(status=status)
    return PaginatedResponse[CrawlRunListItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + len(items) < total,
        has_prev=page > 1,
    )


@router.get(
    "/crawl-runs/{crawl_run_id}",
    response_model=CrawlRunRead,
    summary="Get crawl run",
)
def get_crawl_run(
    crawl_run_id: str,
    service: CrawlRunService = Depends(get_crawl_run_service),
):
    return service.get_crawl_run(crawl_run_id)


@router.post(
    "/crawl-runs/{crawl_run_id}/mark-running",
    response_model=CrawlRunRead,
    summary="Mark crawl run running",
)
def mark_crawl_run_running(
    crawl_run_id: str,
    service: CrawlRunService = Depends(get_crawl_run_service),
):
    return service.mark_running(crawl_run_id)


@router.post(
    "/crawl-runs/{crawl_run_id}/mark-success",
    response_model=CrawlRunRead,
    summary="Mark crawl run success",
)
def mark_crawl_run_success(
    crawl_run_id: str,
    data: CrawlRunMarkSuccessRequest,
    service: CrawlRunService = Depends(get_crawl_run_service),
):
    return service.mark_success(
        crawl_run_id,
        pages_found=data.pages_found,
        pages_crawled=data.pages_crawled,
    )


@router.post(
    "/crawl-runs/{crawl_run_id}/mark-failed",
    response_model=CrawlRunRead,
    summary="Mark crawl run failed",
)
def mark_crawl_run_failed(
    crawl_run_id: str,
    data: CrawlRunMarkFailedRequest,
    service: CrawlRunService = Depends(get_crawl_run_service),
):
    return service.mark_failed(crawl_run_id, data.error_message)
