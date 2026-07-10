from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.job_discovery_link import JobDiscoveryLink
from app.repositories.base import BaseRepository


class JobDiscoveryLinkRepository(BaseRepository[JobDiscoveryLink]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, JobDiscoveryLink)

    def get_by_candidate_id(self, candidate_id: str) -> JobDiscoveryLink | None:
        stmt = (
            select(JobDiscoveryLink)
            .options(selectinload(JobDiscoveryLink.job))
            .where(JobDiscoveryLink.discovery_candidate_id == candidate_id)
        )
        return self.session.scalar(stmt)

    def get_by_job_and_candidate(
        self, job_id: str, candidate_id: str
    ) -> JobDiscoveryLink | None:
        stmt = select(JobDiscoveryLink).where(
            JobDiscoveryLink.job_id == job_id,
            JobDiscoveryLink.discovery_candidate_id == candidate_id,
        )
        return self.session.scalar(stmt)

    def ensure_link(self, job_id: str, candidate_id: str) -> JobDiscoveryLink:
        existing = self.get_by_job_and_candidate(job_id, candidate_id)
        if existing is not None:
            return existing
        by_candidate = self.get_by_candidate_id(candidate_id)
        if by_candidate is not None:
            return by_candidate
        return self.create(JobDiscoveryLink(job_id=job_id, discovery_candidate_id=candidate_id))
