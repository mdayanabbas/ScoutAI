from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_enrichment_attempt import JobEnrichmentAttempt
from app.repositories.base import BaseRepository
from app.utils.enums import JobEnrichmentAttemptStatus


class JobEnrichmentAttemptRepository(BaseRepository[JobEnrichmentAttempt]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, JobEnrichmentAttempt)

    def create_attempt(self, attempt: JobEnrichmentAttempt) -> JobEnrichmentAttempt:
        return self.create(attempt)

    def list_by_job_id(self, job_id: str) -> list[JobEnrichmentAttempt]:
        stmt = (
            select(JobEnrichmentAttempt)
            .where(JobEnrichmentAttempt.job_id == job_id)
            .order_by(JobEnrichmentAttempt.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_by_job_id_paginated(
        self, job_id: str, *, limit: int = 20, offset: int = 0
    ) -> list[JobEnrichmentAttempt]:
        stmt = (
            select(JobEnrichmentAttempt)
            .where(JobEnrichmentAttempt.job_id == job_id)
            .order_by(JobEnrichmentAttempt.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def count_by_job_id(self, job_id: str) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(JobEnrichmentAttempt)
            .where(JobEnrichmentAttempt.job_id == job_id)
        )
        return self.session.scalar(stmt) or 0

    def get_running_for_job(self, job_id: str) -> JobEnrichmentAttempt | None:
        stmt = (
            select(JobEnrichmentAttempt)
            .where(
                JobEnrichmentAttempt.job_id == job_id,
                JobEnrichmentAttempt.status == JobEnrichmentAttemptStatus.RUNNING.value,
            )
            .order_by(JobEnrichmentAttempt.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def get_latest_for_job(self, job_id: str) -> JobEnrichmentAttempt | None:
        stmt = (
            select(JobEnrichmentAttempt)
            .where(JobEnrichmentAttempt.job_id == job_id)
            .order_by(JobEnrichmentAttempt.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def get_latest_by_provider(
        self, job_id: str, provider: str
    ) -> JobEnrichmentAttempt | None:
        stmt = (
            select(JobEnrichmentAttempt)
            .where(
                JobEnrichmentAttempt.job_id == job_id,
                JobEnrichmentAttempt.provider == provider,
            )
            .order_by(JobEnrichmentAttempt.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def update_attempt(
        self, attempt: JobEnrichmentAttempt, data: dict[str, Any]
    ) -> JobEnrichmentAttempt:
        return self.update(attempt, data)

    def mark_succeeded(
        self,
        attempt: JobEnrichmentAttempt,
        *,
        reason: str | None = None,
        extracted_data: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
        field_confidence: dict[str, Any] | None = None,
    ) -> JobEnrichmentAttempt:
        return self._complete(
            attempt,
            JobEnrichmentAttemptStatus.SUCCEEDED,
            reason=reason,
            extracted_data=extracted_data,
            evidence=evidence,
            field_confidence=field_confidence,
        )

    def mark_partial(
        self,
        attempt: JobEnrichmentAttempt,
        *,
        reason: str | None = None,
        extracted_data: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
        field_confidence: dict[str, Any] | None = None,
    ) -> JobEnrichmentAttempt:
        return self._complete(
            attempt,
            JobEnrichmentAttemptStatus.PARTIAL,
            reason=reason,
            extracted_data=extracted_data,
            evidence=evidence,
            field_confidence=field_confidence,
        )

    def mark_unresolved(
        self,
        attempt: JobEnrichmentAttempt,
        *,
        reason: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> JobEnrichmentAttempt:
        return self._complete(
            attempt,
            JobEnrichmentAttemptStatus.UNRESOLVED,
            reason=reason,
            evidence=evidence,
        )

    def mark_failed(
        self, attempt: JobEnrichmentAttempt, error_message: str
    ) -> JobEnrichmentAttempt:
        return self._complete(
            attempt,
            JobEnrichmentAttemptStatus.FAILED,
            error_message=_safe_error_message(error_message),
        )

    def _complete(
        self,
        attempt: JobEnrichmentAttempt,
        status: JobEnrichmentAttemptStatus,
        *,
        reason: str | None = None,
        error_message: str | None = None,
        extracted_data: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
        field_confidence: dict[str, Any] | None = None,
    ) -> JobEnrichmentAttempt:
        values: dict[str, Any] = {
            "status": status.value,
            "finished_at": datetime.now(timezone.utc),
        }
        if reason is not None:
            values["reason"] = reason
        if error_message is not None:
            values["error_message"] = error_message
        if extracted_data is not None:
            values["extracted_data_json"] = extracted_data
        if evidence is not None:
            values["evidence_json"] = evidence
        if field_confidence is not None:
            values["field_confidence_json"] = field_confidence
        return self.update(attempt, values)


def _safe_error_message(value: str) -> str:
    return value.strip() or "Job enrichment failed"
