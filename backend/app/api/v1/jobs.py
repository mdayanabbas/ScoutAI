from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.job import JobCreate, JobListItem, JobRead, JobUpdate
from app.services.job_service import JobService
from app.utils.enums import JobStatus, RemoteType, RoleCategory

router = APIRouter(tags=["jobs"])


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db)


@router.post(
    "/companies/{company_id}/jobs",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update company job",
)
def create_or_update_company_job(
    company_id: str,
    data: JobCreate,
    service: JobService = Depends(get_job_service),
):
    return service.create_or_update_job(company_id, data)


@router.get(
    "/jobs",
    response_model=PaginatedResponse[JobListItem],
    summary="List jobs",
)
def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    company_id: str | None = None,
    role_category: RoleCategory | None = None,
    remote_type: RemoteType | None = None,
    status: JobStatus | None = None,
    search: str | None = None,
    service: JobService = Depends(get_job_service),
):
    offset = (page - 1) * page_size
    items = service.list_jobs(
        offset=offset,
        limit=page_size,
        company_id=company_id,
        role_category=role_category,
        remote_type=remote_type,
        status=status,
        search=search,
    )
    total = service.count_jobs(
        company_id=company_id,
        role_category=role_category,
        remote_type=remote_type,
        status=status,
        search=search,
    )
    return PaginatedResponse[JobListItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + len(items) < total,
        has_prev=page > 1,
    )


@router.get(
    "/companies/{company_id}/jobs",
    response_model=PaginatedResponse[JobListItem],
    summary="List company jobs",
)
def list_company_jobs(
    company_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role_category: RoleCategory | None = None,
    remote_type: RemoteType | None = None,
    status: JobStatus | None = None,
    search: str | None = None,
    service: JobService = Depends(get_job_service),
):
    offset = (page - 1) * page_size
    items = service.list_company_jobs(
        company_id,
        offset=offset,
        limit=page_size,
        role_category=role_category,
        remote_type=remote_type,
        status=status,
        search=search,
    )
    total = service.count_company_jobs(
        company_id,
        role_category=role_category,
        remote_type=remote_type,
        status=status,
        search=search,
    )
    return PaginatedResponse[JobListItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + len(items) < total,
        has_prev=page > 1,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobRead,
    summary="Get job",
)
def get_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
):
    return service.get_job(job_id)


@router.patch(
    "/jobs/{job_id}",
    response_model=JobRead,
    summary="Update job",
)
def update_job(
    job_id: str,
    data: JobUpdate,
    service: JobService = Depends(get_job_service),
):
    return service.update_job(job_id, data)


@router.delete(
    "/jobs/{job_id}",
    response_model=MessageResponse,
    summary="Delete job",
)
def delete_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
):
    service.delete_job(job_id)
    return MessageResponse(message="Job deleted successfully")
