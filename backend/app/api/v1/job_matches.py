from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job_match import (
    JobMatchBatchRead,
    JobMatchListItemRead,
    JobMatchListRead,
    JobMatchRead,
    JobMatchScoreRequest,
)
from app.services.job_matching_service import JobMatchingService

router = APIRouter(prefix="/job-matches", tags=["job-matches"])


def get_job_matching_service(db: Session = Depends(get_db)) -> JobMatchingService:
    return JobMatchingService(db)


@router.post("/score", response_model=JobMatchBatchRead, summary="Score jobs for current matching profile")
def score_job_matches(
    data: JobMatchScoreRequest | None = None,
    service: JobMatchingService = Depends(get_job_matching_service),
):
    profile = service.current_profile()
    request = data or JobMatchScoreRequest()
    return service.score_jobs(profile.id, job_ids=request.job_ids, limit=request.limit, force=request.force)


@router.get("", response_model=JobMatchListRead, summary="List recommended job matches")
def list_job_matches(
    eligibility_status: str | None = None,
    match_tier: str | None = None,
    remote_eligibility: str | None = None,
    minimum_score: float | None = Query(default=None, ge=0, le=100),
    include_unsuitable: bool = False,
    target_role: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="recommended", pattern="^(recommended|score|newest|salary)$"),
    service: JobMatchingService = Depends(get_job_matching_service),
):
    profile = service.current_profile()
    matches = service.list_matches(
        profile.id,
        eligibility_status=eligibility_status,
        match_tier=match_tier,
        remote_eligibility=remote_eligibility,
        minimum_score=minimum_score,
        include_unsuitable=include_unsuitable,
        limit=limit,
        offset=offset,
        order_by=order_by,
    )
    if target_role:
        matches = [
            item
            for item in matches
            if (item.score_breakdown_json or {}).get("role", "").lower().find(target_role.lower()) >= 0
            or any(target_role.lower() in signal.lower() for signal in (item.positive_signals_json or []))
        ]
    items = [JobMatchListItemRead.from_match(item, is_stale=service.is_stale(item, profile)) for item in matches]
    return JobMatchListRead(items=items, total=len(items), limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobMatchRead, summary="Get current profile match for a job")
def get_job_match(
    job_id: str,
    service: JobMatchingService = Depends(get_job_matching_service),
):
    profile = service.current_profile()
    match = service.get_match(profile.id, job_id)
    setattr(match, "is_stale", service.is_stale(match, profile))
    return match
