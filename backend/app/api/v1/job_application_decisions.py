from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job_application_decision import (
    JobApplicationDecisionCreate,
    JobApplicationDecisionListRead,
    JobApplicationDecisionRead,
    JobApplicationDecisionStatusCountsRead,
    JobApplicationDecisionUpdate,
)
from app.services.job_application_decision_service import JobApplicationDecisionService

router = APIRouter(prefix="/job-decisions", tags=["job-decisions"])


def get_job_application_decision_service(db: Session = Depends(get_db)) -> JobApplicationDecisionService:
    return JobApplicationDecisionService(db)


@router.get("/status-counts", response_model=JobApplicationDecisionStatusCountsRead)
def get_job_application_decision_status_counts(
    service: JobApplicationDecisionService = Depends(get_job_application_decision_service),
):
    return service.status_counts()


@router.post(
    "/jobs/{job_id}",
    response_model=JobApplicationDecisionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_job_application_decision(
    job_id: str,
    data: JobApplicationDecisionCreate | None = None,
    service: JobApplicationDecisionService = Depends(get_job_application_decision_service),
):
    return service.create_or_update_for_job(job_id, data or JobApplicationDecisionCreate())


@router.get("/jobs/{job_id}", response_model=JobApplicationDecisionRead)
def get_job_application_decision_for_job(
    job_id: str,
    service: JobApplicationDecisionService = Depends(get_job_application_decision_service),
):
    return service.get_for_job(job_id)


@router.get("", response_model=JobApplicationDecisionListRead)
def list_job_application_decisions(
    status_filter: str | None = Query(default=None, alias="status"),
    include_archived: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: JobApplicationDecisionService = Depends(get_job_application_decision_service),
):
    return service.list_decisions(
        status=status_filter,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.patch("/{decision_id}", response_model=JobApplicationDecisionRead)
def update_job_application_decision(
    decision_id: str,
    data: JobApplicationDecisionUpdate,
    service: JobApplicationDecisionService = Depends(get_job_application_decision_service),
):
    return service.update_decision(decision_id, data)


@router.post("/{decision_id}/archive", response_model=JobApplicationDecisionRead)
def archive_job_application_decision(
    decision_id: str,
    service: JobApplicationDecisionService = Depends(get_job_application_decision_service),
):
    return service.archive_decision(decision_id)


@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_application_decision(
    decision_id: str,
    service: JobApplicationDecisionService = Depends(get_job_application_decision_service),
):
    service.delete_decision(decision_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
