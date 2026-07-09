from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_enrichment_attempt import CompanyEnrichmentAttempt
from app.repositories.base import BaseRepository
from app.utils.enums import (
    CompanyEnrichmentDecision,
    CompanyEnrichmentStatus,
)


class CompanyEnrichmentAttemptRepository(BaseRepository[CompanyEnrichmentAttempt]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CompanyEnrichmentAttempt)

    def create_attempt(
        self, attempt: CompanyEnrichmentAttempt
    ) -> CompanyEnrichmentAttempt:
        return self.create(attempt)

    def list_by_candidate(self, candidate_id: str) -> list[CompanyEnrichmentAttempt]:
        stmt = (
            select(CompanyEnrichmentAttempt)
            .where(CompanyEnrichmentAttempt.discovery_candidate_id == candidate_id)
            .order_by(CompanyEnrichmentAttempt.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def mark_running(
        self, attempt: CompanyEnrichmentAttempt
    ) -> CompanyEnrichmentAttempt:
        return self.update(
            attempt,
            {
                "status": CompanyEnrichmentStatus.RUNNING,
                "started_at": datetime.now(timezone.utc),
            },
        )

    def mark_resolved(
        self, attempt: CompanyEnrichmentAttempt, data: dict[str, Any]
    ) -> CompanyEnrichmentAttempt:
        values = dict(data)
        values.update(
            {
                "status": CompanyEnrichmentStatus.RESOLVED,
                "finished_at": datetime.now(timezone.utc),
            }
        )
        return self.update(attempt, values)

    def mark_unresolved(
        self,
        attempt: CompanyEnrichmentAttempt,
        reason: str,
        evidence: dict[str, Any] | None = None,
    ) -> CompanyEnrichmentAttempt:
        return self.update(
            attempt,
            {
                "status": CompanyEnrichmentStatus.UNRESOLVED,
                "decision": CompanyEnrichmentDecision.UNRESOLVED,
                "reason": reason,
                "evidence_json": evidence,
                "finished_at": datetime.now(timezone.utc),
            },
        )

    def mark_failed(
        self, attempt: CompanyEnrichmentAttempt, error_message: str
    ) -> CompanyEnrichmentAttempt:
        return self.update(
            attempt,
            {
                "status": CompanyEnrichmentStatus.FAILED,
                "decision": CompanyEnrichmentDecision.FAILED,
                "error_message": error_message,
                "finished_at": datetime.now(timezone.utc),
            },
        )

    def list_recent(
        self,
        offset: int = 0,
        limit: int = 100,
        status: CompanyEnrichmentStatus | None = None,
    ) -> list[CompanyEnrichmentAttempt]:
        stmt = select(CompanyEnrichmentAttempt)
        if status is not None:
            stmt = stmt.where(CompanyEnrichmentAttempt.status == status)
        stmt = (
            stmt.order_by(CompanyEnrichmentAttempt.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
