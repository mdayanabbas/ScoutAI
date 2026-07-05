from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardSummary,
    RecentActivityItem,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get dashboard summary",
)
def get_dashboard_summary(
    service: DashboardService = Depends(get_dashboard_service),
):
    return service.get_summary()


@router.get(
    "/activity",
    response_model=list[RecentActivityItem],
    summary="Get dashboard activity",
)
def get_dashboard_activity(
    limit: int = Query(default=20, ge=1, le=100),
    service: DashboardService = Depends(get_dashboard_service),
):
    return service.get_recent_activity(limit=limit)


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get dashboard overview",
)
def get_dashboard(
    service: DashboardService = Depends(get_dashboard_service),
):
    return DashboardResponse(
        summary=service.get_summary(),
        recent_activity=service.get_recent_activity(),
    )
