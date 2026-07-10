import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.db.session import get_db
from app.jobs.job_source_detector import JobSourceDetector
from app.repositories.job_enrichment_attempt_repository import (
    JobEnrichmentAttemptRepository,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.job import (
    JobBatchEnrichmentRead,
    JobBatchEnrichmentRequest,
    JobCreate,
    JobEnrichmentAttemptListRead,
    JobEnrichmentAttemptRead,
    JobEnrichmentRunRead,
    JobListItem,
    JobRead,
    JobUpdate,
)
from app.schemas.job_source import JobSourceDetectionRead
from app.services.job_batch_enrichment_service import JobBatchEnrichmentService
from app.services.job_detail_enrichment_service import JobDetailEnrichmentService
from app.services.job_service import JobService
from app.utils.enums import JobStatus, RemoteType, RoleCategory

router = APIRouter(tags=["jobs"])
logger = logging.getLogger(__name__)


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db)


def get_job_detail_enrichment_service(
    db: Session = Depends(get_db),
) -> JobDetailEnrichmentService:
    return JobDetailEnrichmentService(db)


def get_job_batch_enrichment_service(
    db: Session = Depends(get_db),
) -> JobBatchEnrichmentService:
    return JobBatchEnrichmentService(db)


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


@router.post(
    "/jobs/enrichment/batch",
    response_model=JobBatchEnrichmentRead,
    summary="Enrich a bounded batch of jobs",
)
async def enrich_jobs_batch(
    data: JobBatchEnrichmentRequest | None = None,
    service: JobBatchEnrichmentService = Depends(get_job_batch_enrichment_service),
):
    settings = get_settings()
    request = data or JobBatchEnrichmentRequest()
    limit = request.limit or settings.JOB_ENRICHMENT_BATCH_DEFAULT_LIMIT
    if limit > settings.JOB_ENRICHMENT_BATCH_MAX_LIMIT:
        raise ValidationAppError(
            "limit exceeds maximum",
            {"limit": f"maximum {settings.JOB_ENRICHMENT_BATCH_MAX_LIMIT}"},
        )
    if request.job_ids is not None and len(set(request.job_ids)) > settings.JOB_ENRICHMENT_BATCH_MAX_LIMIT:
        raise ValidationAppError(
            "Too many job IDs",
            {"job_ids": f"maximum {settings.JOB_ENRICHMENT_BATCH_MAX_LIMIT}"},
        )
    logger.info(
        "Batch enrichment requested",
        extra={
            "limit": limit,
            "explicit_job_ids": request.job_ids is not None,
            "include_failed": request.include_failed,
            "force": request.force,
        },
    )
    return await service.enrich_jobs(
        limit=limit,
        job_ids=request.job_ids,
        include_failed=request.include_failed,
        force=request.force,
    )


@router.post(
    "/jobs/{job_id}/enrich",
    response_model=JobEnrichmentRunRead,
    summary="Enrich a single job",
)
async def enrich_job(
    job_id: str,
    db: Session = Depends(get_db),
    service: JobDetailEnrichmentService = Depends(get_job_detail_enrichment_service),
):
    job_service = JobService(db)
    job_service.get_job(job_id)
    running = JobEnrichmentAttemptRepository(db).get_running_for_job(job_id)
    if running is not None:
        logger.info("Concurrent job enrichment rejected", extra={"job_id": job_id})
        raise ConflictError("Job enrichment is already running")
    logger.info("API enrichment requested", extra={"job_id": job_id})
    result = await service.enrich_job(job_id)
    attempt = (
        JobEnrichmentAttemptRepository(db).get_by_id(result.attempt_id)
        if result.attempt_id
        else None
    )
    refreshed_job = job_service.get_job(job_id)
    logger.info(
        "API enrichment completed",
        extra={"job_id": job_id, "status": result.status, "reason": result.reason},
    )
    return JobEnrichmentRunRead(
        job_id=result.job_id,
        provider=result.provider,
        status=result.status,
        reason=result.reason,
        source_type=result.source_type,
        source_url=result.source_url,
        canonical_url=result.canonical_url,
        fields_updated=result.updated_fields,
        fields_preserved=result.preserved_fields,
        warnings=result.warnings,
        enrichment_confidence=result.enrichment_confidence,
        attempt=attempt,
        job=refreshed_job if result.status in {"enriched", "partially_enriched"} else None,
    )


@router.get(
    "/jobs/{job_id}/enrichment-attempts",
    response_model=JobEnrichmentAttemptListRead,
    summary="List job enrichment attempts",
)
def list_job_enrichment_attempts(
    job_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    service: JobService = Depends(get_job_service),
):
    service.get_job(job_id)
    repository = JobEnrichmentAttemptRepository(db)
    logger.info(
        "Attempt history requested",
        extra={"job_id": job_id, "limit": limit, "offset": offset},
    )
    return JobEnrichmentAttemptListRead(
        items=repository.list_by_job_id_paginated(job_id, limit=limit, offset=offset),
        total=repository.count_by_job_id(job_id),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/jobs/{job_id}/enrichment-attempts/latest",
    response_model=JobEnrichmentAttemptRead,
    summary="Get latest job enrichment attempt",
)
def get_latest_job_enrichment_attempt(
    job_id: str,
    db: Session = Depends(get_db),
    service: JobService = Depends(get_job_service),
):
    service.get_job(job_id)
    attempt = JobEnrichmentAttemptRepository(db).get_latest_for_job(job_id)
    if attempt is None:
        raise NotFoundError("Job enrichment attempt not found")
    return attempt


@router.get(
    "/jobs/{job_id}/source-detection",
    response_model=JobSourceDetectionRead,
    summary="Inspect job source detection",
)
def inspect_job_source_detection(
    job_id: str,
    service: JobService = Depends(get_job_service),
):
    job = service.get_job(job_id)
    company_domain = getattr(job.company, "normalized_domain", None)
    detection = JobSourceDetector().detect(
        job.job_url,
        company_domain=company_domain,
        source_platform=job.source_platform,
    )
    logger.info(
        "Source detection inspected",
        extra={"job_id": job_id, "source_type": detection.source_type.value},
    )
    return JobSourceDetectionRead(
        source_type=detection.source_type.value,
        original_url=detection.original_url,
        canonical_url=detection.canonical_url,
        normalized_domain=detection.normalized_domain,
        provider=detection.provider,
        company_slug=detection.company_slug,
        job_identifier=detection.job_identifier,
        board_slug=detection.board_slug,
        is_first_party=detection.is_first_party,
        supported=detection.supported,
        confidence=detection.confidence,
        reason=detection.reason,
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
