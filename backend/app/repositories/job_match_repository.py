from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.job import Job
from app.models.job_match import JobMatch
from app.repositories.base import BaseRepository


class JobMatchRepository(BaseRepository[JobMatch]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, JobMatch)

    def get_by_profile_and_job(self, profile_id: str, job_id: str) -> JobMatch | None:
        stmt = (
            select(JobMatch)
            .options(selectinload(JobMatch.job))
            .where(
                JobMatch.job_matching_profile_id == profile_id,
                JobMatch.job_id == job_id,
            )
        )
        return self.session.scalar(stmt)

    def upsert_match(self, profile_id: str, job_id: str, data: dict[str, Any]) -> tuple[JobMatch, str]:
        existing = self.get_by_profile_and_job(profile_id, job_id)
        if existing is not None:
            return self.update(existing, data), "updated"
        return self.create(JobMatch(job_matching_profile_id=profile_id, job_id=job_id, **data)), "created"

    def list_for_profile(
        self,
        profile_id: str,
        *,
        eligibility_status: str | None = None,
        match_tier: str | None = None,
        remote_eligibility: str | None = None,
        minimum_score: float | None = None,
        include_unsuitable: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[JobMatch]:
        stmt = (
            select(JobMatch)
            .options(selectinload(JobMatch.job).selectinload(Job.company))
            .where(JobMatch.job_matching_profile_id == profile_id)
        )
        if eligibility_status:
            stmt = stmt.where(JobMatch.eligibility_status == eligibility_status)
        if match_tier:
            stmt = stmt.where(JobMatch.match_tier == match_tier)
        if remote_eligibility:
            stmt = stmt.where(JobMatch.remote_eligibility == remote_eligibility)
        if minimum_score is not None:
            stmt = stmt.where(JobMatch.total_score >= minimum_score)
        if not include_unsuitable:
            stmt = stmt.where(JobMatch.eligibility_status != "unsuitable")
        stmt = stmt.order_by(JobMatch.total_score.desc(), JobMatch.scored_at.desc()).offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_all_for_profile(self, profile_id: str) -> list[JobMatch]:
        stmt = select(JobMatch).where(JobMatch.job_matching_profile_id == profile_id)
        return list(self.session.scalars(stmt).all())
