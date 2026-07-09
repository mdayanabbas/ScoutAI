from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.discovery_job_ingestion import (
    DiscoveryJobIngestionResult,
    DiscoveryRunJobIngestionResult,
)
from app.services.discovery_job_ingestion_service import DiscoveryJobIngestionService

router = APIRouter(prefix="/discovery", tags=["discovery"])


def get_discovery_job_ingestion_service(
    db: Session = Depends(get_db),
) -> DiscoveryJobIngestionService:
    return DiscoveryJobIngestionService(db)


@router.post(
    "/candidates/{candidate_id}/ingest-job",
    response_model=DiscoveryJobIngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest discovery candidate as job",
)
def ingest_candidate_job(
    candidate_id: str,
    service: DiscoveryJobIngestionService = Depends(
        get_discovery_job_ingestion_service
    ),
):
    return service.ingest_candidate(candidate_id)


@router.post(
    "/runs/{run_id}/ingest-jobs",
    response_model=DiscoveryRunJobIngestionResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest discovery run jobs",
)
def ingest_run_jobs(
    run_id: str,
    limit: int | None = Query(default=None, ge=1),
    service: DiscoveryJobIngestionService = Depends(
        get_discovery_job_ingestion_service
    ),
):
    return service.ingest_discovery_run(run_id, limit=limit)
