from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.job_discovery_link import JobDiscoveryLink
from app.repositories.base import BaseRepository


class JobDiscoveryLinkRepository(BaseRepository[JobDiscoveryLink]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, JobDiscoveryLink)

    def get_by_candidate_id(self, candidate_id: str) -> JobDiscoveryLink | None:
        """Return one deterministic link for compatibility; use list_by_candidate_id for all links."""
        stmt = (
            select(JobDiscoveryLink)
            .options(selectinload(JobDiscoveryLink.job))
            .where(JobDiscoveryLink.discovery_candidate_id == candidate_id)
            .order_by(JobDiscoveryLink.created_at.asc(), JobDiscoveryLink.id.asc())
        )
        return self.session.scalar(stmt)

    def list_by_candidate_id(self, candidate_id: str) -> list[JobDiscoveryLink]:
        stmt = (
            select(JobDiscoveryLink)
            .options(selectinload(JobDiscoveryLink.job))
            .where(JobDiscoveryLink.discovery_candidate_id == candidate_id)
            .order_by(JobDiscoveryLink.created_at.asc(), JobDiscoveryLink.id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_by_job_id(self, job_id: str) -> list[JobDiscoveryLink]:
        stmt = (
            select(JobDiscoveryLink)
            .options(selectinload(JobDiscoveryLink.discovery_candidate))
            .where(JobDiscoveryLink.job_id == job_id)
            .order_by(JobDiscoveryLink.created_at.asc(), JobDiscoveryLink.id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def count_by_candidate_id(self, candidate_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(JobDiscoveryLink)
            .where(JobDiscoveryLink.discovery_candidate_id == candidate_id)
        )
        return self.session.scalar(stmt) or 0

    def get_by_job_and_candidate(
        self, job_id: str, candidate_id: str
    ) -> JobDiscoveryLink | None:
        stmt = select(JobDiscoveryLink).where(
            JobDiscoveryLink.job_id == job_id,
            JobDiscoveryLink.discovery_candidate_id == candidate_id,
        )
        return self.session.scalar(stmt)

    def exists(self, job_id: str, candidate_id: str) -> bool:
        return self.get_by_job_and_candidate(job_id, candidate_id) is not None

    def create_link(self, job_id: str, candidate_id: str) -> JobDiscoveryLink:
        return self.create(JobDiscoveryLink(job_id=job_id, discovery_candidate_id=candidate_id))

    def get_or_create_link(self, job_id: str, candidate_id: str) -> JobDiscoveryLink:
        existing = self.get_by_job_and_candidate(job_id, candidate_id)
        if existing is not None:
            return existing
        try:
            return self.create_link(job_id, candidate_id)
        except IntegrityError:
            self.session.rollback()
            existing = self.get_by_job_and_candidate(job_id, candidate_id)
            if existing is None:
                raise
            return existing

    def ensure_link(self, job_id: str, candidate_id: str) -> JobDiscoveryLink:
        return self.get_or_create_link(job_id, candidate_id)
