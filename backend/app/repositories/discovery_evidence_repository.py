from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.discovery_evidence import DiscoveryEvidence
from app.repositories.base import BaseRepository


class DiscoveryEvidenceRepository(BaseRepository[DiscoveryEvidence]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DiscoveryEvidence)

    def create_evidence(self, evidence: DiscoveryEvidence) -> DiscoveryEvidence:
        return self.create(evidence)

    def list_by_candidate(self, candidate_id: str) -> list[DiscoveryEvidence]:
        stmt = select(DiscoveryEvidence).where(
            DiscoveryEvidence.discovery_candidate_id == candidate_id
        )
        return list(self.session.scalars(stmt).all())

    def create_many(self, items: list[DiscoveryEvidence]) -> list[DiscoveryEvidence]:
        self.session.add_all(items)
        self.session.commit()
        for item in items:
            self.session.refresh(item)
        return items
