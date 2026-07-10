from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.job_board_expansion_link import JobBoardExpansionLink
from app.repositories.base import BaseRepository


class JobBoardExpansionLinkRepository(BaseRepository[JobBoardExpansionLink]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, JobBoardExpansionLink)

    def get_by_parent_and_child(
        self, parent_job_id: str, child_job_id: str
    ) -> JobBoardExpansionLink | None:
        stmt = select(JobBoardExpansionLink).where(
            JobBoardExpansionLink.parent_job_id == parent_job_id,
            JobBoardExpansionLink.child_job_id == child_job_id,
        )
        return self.session.scalar(stmt)

    def exists(self, parent_job_id: str, child_job_id: str) -> bool:
        return self.get_by_parent_and_child(parent_job_id, child_job_id) is not None

    def create_link(
        self,
        *,
        parent_job_id: str,
        child_job_id: str,
        discovery_candidate_id: str | None,
        provider: str,
    ) -> JobBoardExpansionLink:
        return self.create(
            JobBoardExpansionLink(
                parent_job_id=parent_job_id,
                child_job_id=child_job_id,
                discovery_candidate_id=discovery_candidate_id,
                provider=provider,
            )
        )

    def get_or_create_link(
        self,
        *,
        parent_job_id: str,
        child_job_id: str,
        discovery_candidate_id: str | None,
        provider: str,
    ) -> JobBoardExpansionLink:
        existing = self.get_by_parent_and_child(parent_job_id, child_job_id)
        if existing is not None:
            return existing
        try:
            return self.create_link(
                parent_job_id=parent_job_id,
                child_job_id=child_job_id,
                discovery_candidate_id=discovery_candidate_id,
                provider=provider,
            )
        except IntegrityError:
            self.session.rollback()
            existing = self.get_by_parent_and_child(parent_job_id, child_job_id)
            if existing is None:
                raise
            return existing

    def list_children(self, parent_job_id: str) -> list[JobBoardExpansionLink]:
        stmt = (
            select(JobBoardExpansionLink)
            .options(selectinload(JobBoardExpansionLink.child_job))
            .where(JobBoardExpansionLink.parent_job_id == parent_job_id)
            .order_by(JobBoardExpansionLink.created_at.asc(), JobBoardExpansionLink.id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_parents(self, child_job_id: str) -> list[JobBoardExpansionLink]:
        stmt = (
            select(JobBoardExpansionLink)
            .options(selectinload(JobBoardExpansionLink.parent_job))
            .where(JobBoardExpansionLink.child_job_id == child_job_id)
            .order_by(JobBoardExpansionLink.created_at.asc(), JobBoardExpansionLink.id.asc())
        )
        return list(self.session.scalars(stmt).all())
