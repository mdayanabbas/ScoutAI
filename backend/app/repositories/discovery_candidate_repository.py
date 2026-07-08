from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.discovery_candidate import DiscoveryCandidate
from app.repositories.base import BaseRepository
from app.utils.enums import DiscoveryCandidateStatus, DiscoverySource


class DiscoveryCandidateRepository(BaseRepository[DiscoveryCandidate]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DiscoveryCandidate)

    def create_candidate(self, candidate: DiscoveryCandidate) -> DiscoveryCandidate:
        return self.create(candidate)

    def get_by_id(self, id: str) -> DiscoveryCandidate | None:
        stmt = (
            select(DiscoveryCandidate)
            .options(selectinload(DiscoveryCandidate.evidence))
            .where(DiscoveryCandidate.id == id)
        )
        return self.session.scalar(stmt)

    def get_by_source_identifier(
        self,
        run_id: str,
        source: DiscoverySource,
        source_identifier: str,
    ) -> DiscoveryCandidate | None:
        stmt = select(DiscoveryCandidate).where(
            DiscoveryCandidate.discovery_run_id == run_id,
            DiscoveryCandidate.source == source,
            DiscoveryCandidate.source_identifier == source_identifier,
        )
        return self.session.scalar(stmt)

    def list_by_run(
        self,
        run_id: str,
        offset: int = 0,
        limit: int = 100,
        status: DiscoveryCandidateStatus | None = None,
    ) -> list[DiscoveryCandidate]:
        stmt = (
            select(DiscoveryCandidate)
            .options(selectinload(DiscoveryCandidate.evidence))
            .where(DiscoveryCandidate.discovery_run_id == run_id)
        )
        if status is not None:
            stmt = stmt.where(DiscoveryCandidate.status == status)
        stmt = stmt.order_by(DiscoveryCandidate.created_at.asc()).offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_by_run(
        self,
        run_id: str,
        status: DiscoveryCandidateStatus | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(DiscoveryCandidate).where(
            DiscoveryCandidate.discovery_run_id == run_id
        )
        if status is not None:
            stmt = stmt.where(DiscoveryCandidate.status == status)
        return self.session.scalar(stmt) or 0

    def update_candidate(
        self, candidate: DiscoveryCandidate, data: dict[str, Any]
    ) -> DiscoveryCandidate:
        return self.update(candidate, data)
