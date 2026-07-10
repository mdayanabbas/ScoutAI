import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationAppError
from app.jobs.job_source_detector import JobSourceDetector
from app.models.job import Job
from app.repositories.job_enrichment_attempt_repository import (
    JobEnrichmentAttemptRepository,
)
from app.repositories.job_repository import JobRepository
from app.services.job_detail_enrichment_service import (
    JobDetailEnrichmentService,
    JobEnrichmentResult,
)
from app.utils.enums import JobSourceType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobBatchEnrichmentItem:
    job_id: str
    company_name: str | None = None
    previous_title: str | None = None
    current_title: str | None = None
    provider: str | None = None
    status: str = "skipped"
    reason: str | None = None
    fields_updated: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    attempt_id: str | None = None
    enrichment_confidence: float | None = None


@dataclass(frozen=True)
class JobBatchEnrichmentResult:
    jobs_examined: int
    jobs_enriched: int
    jobs_partially_enriched: int
    jobs_unresolved: int
    jobs_failed: int
    jobs_skipped: int
    jobs_missing: int
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    results: list[JobBatchEnrichmentItem]


class JobBatchEnrichmentService:
    def __init__(
        self,
        session: Session,
        *,
        detail_service: JobDetailEnrichmentService | None = None,
        delay_ms: int | None = None,
    ) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.attempt_repository = JobEnrichmentAttemptRepository(session)
        self.detail_service = detail_service or JobDetailEnrichmentService(session)
        self.source_detector = JobSourceDetector()
        settings = get_settings()
        self.max_limit = settings.JOB_ENRICHMENT_BATCH_MAX_LIMIT
        self.default_limit = settings.JOB_ENRICHMENT_BATCH_DEFAULT_LIMIT
        self.delay_ms = settings.JOB_ENRICHMENT_BATCH_DELAY_MS if delay_ms is None else delay_ms

    def select_jobs(
        self,
        *,
        limit: int,
        job_ids: list[str] | None = None,
        include_failed: bool = False,
        force: bool = False,
    ) -> tuple[list[Job], list[str]]:
        self._validate_limit(limit)
        if job_ids is not None:
            unique_ids = _dedupe(job_ids)
            if not unique_ids:
                raise ValidationAppError("job_ids must not be empty")
            if len(unique_ids) > self.max_limit:
                raise ValidationAppError("Too many job IDs", {"job_ids": f"maximum {self.max_limit}"})
            selected: list[Job] = []
            missing: list[str] = []
            for job_id in unique_ids[:limit]:
                job = self.job_repository.get_by_id(job_id)
                if job is None:
                    missing.append(job_id)
                    continue
                selected.append(job)
            return selected, missing
        return (
            self.job_repository.list_jobs_for_enrichment_batch(
                limit=limit,
                include_failed=include_failed,
                force=force,
            ),
            [],
        )

    async def enrich_jobs(
        self,
        *,
        limit: int | None = None,
        job_ids: list[str] | None = None,
        include_failed: bool = False,
        force: bool = False,
    ) -> JobBatchEnrichmentResult:
        effective_limit = limit or self.default_limit
        self._validate_limit(effective_limit)
        started_at = datetime.now(timezone.utc)
        started = perf_counter()
        logger.info(
            "Batch enrichment started",
            extra={
                "limit": effective_limit,
                "explicit_job_ids": job_ids is not None,
                "include_failed": include_failed,
                "force": force,
            },
        )
        jobs, missing_ids = self.select_jobs(
            limit=effective_limit,
            job_ids=job_ids,
            include_failed=include_failed,
            force=force,
        )
        logger.info("Jobs selected", extra={"selected_count": len(jobs), "missing_count": len(missing_ids)})

        results: list[JobBatchEnrichmentItem] = [
            JobBatchEnrichmentItem(job_id=job_id, status="missing", reason="job_not_found")
            for job_id in missing_ids
        ]
        provider_backed_count = 0
        previous_provider_backed = False
        for job in jobs:
            will_call_provider = self._will_call_provider(job)
            if self.delay_ms > 0 and previous_provider_backed and will_call_provider:
                await asyncio.sleep(self.delay_ms / 1000)
            item = await self._process_job(job)
            results.append(item)
            if will_call_provider and item.status not in {"skipped", "missing"}:
                provider_backed_count += 1
                previous_provider_backed = True

        finished_at = datetime.now(timezone.utc)
        counters = _counters(results)
        duration_ms = int((perf_counter() - started) * 1000)
        logger.info(
            "Batch enrichment completed",
            extra={**counters, "duration_ms": duration_ms, "provider_backed_jobs": provider_backed_count},
        )
        return JobBatchEnrichmentResult(
            jobs_examined=len(jobs),
            jobs_enriched=counters["jobs_enriched"],
            jobs_partially_enriched=counters["jobs_partially_enriched"],
            jobs_unresolved=counters["jobs_unresolved"],
            jobs_failed=counters["jobs_failed"],
            jobs_skipped=counters["jobs_skipped"],
            jobs_missing=counters["jobs_missing"],
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            results=results,
        )

    async def _process_job(self, job: Job) -> JobBatchEnrichmentItem:
        previous_title = job.title
        company_name = getattr(job.company, "name", None)
        if self.attempt_repository.get_running_for_job(job.id) is not None:
            logger.info("Job skipped", extra={"job_id": job.id, "reason": "enrichment_already_running"})
            return JobBatchEnrichmentItem(
                job_id=job.id,
                company_name=company_name,
                previous_title=previous_title,
                current_title=job.title,
                status="skipped",
                reason="enrichment_already_running",
            )
        logger.info("Job processing started", extra={"job_id": job.id})
        try:
            result = await self.detail_service.enrich_job(job.id)
            refreshed = self.job_repository.get_by_id(job.id) or job
            logger.info(
                "Job processing completed",
                extra={"job_id": job.id, "status": result.status, "reason": result.reason},
            )
            reason = result.reason
            if result.status == "skipped" and reason == "unsupported_provider_for_current_brick":
                reason = "unsupported_job_source"
            return JobBatchEnrichmentItem(
                job_id=job.id,
                company_name=company_name,
                previous_title=previous_title,
                current_title=refreshed.title,
                provider=result.provider,
                status=result.status,
                reason=reason,
                fields_updated=result.updated_fields,
                warnings=result.warnings,
                attempt_id=result.attempt_id,
                enrichment_confidence=result.enrichment_confidence,
            )
        except Exception as exc:
            self.session.rollback()
            logger.info(
                "Job failed",
                extra={"job_id": job.id, "error": exc.__class__.__name__},
            )
            return JobBatchEnrichmentItem(
                job_id=job.id,
                company_name=company_name,
                previous_title=previous_title,
                current_title=previous_title,
                status="failed",
                reason="job_enrichment_failed",
            )

    def _validate_limit(self, limit: int) -> None:
        if limit < 1:
            raise ValidationAppError("limit must be at least 1")
        if limit > self.max_limit:
            raise ValidationAppError("limit exceeds maximum", {"limit": f"maximum {self.max_limit}"})

    def _will_call_provider(self, job: Job) -> bool:
        if self.attempt_repository.get_running_for_job(job.id) is not None:
            return False
        company_domain = getattr(job.company, "normalized_domain", None)
        detection = self.source_detector.detect(
            job.job_url,
            company_domain=company_domain,
            source_platform=job.source_platform,
        )
        return detection.source_type in {
            JobSourceType.YCOMBINATOR_JOB,
            JobSourceType.ASHBY_JOB_BOARD,
            JobSourceType.FIRST_PARTY_JOB_PAGE,
        }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _counters(results: list[JobBatchEnrichmentItem]) -> dict[str, int]:
    return {
        "jobs_enriched": sum(1 for item in results if item.status == "enriched"),
        "jobs_partially_enriched": sum(1 for item in results if item.status == "partially_enriched"),
        "jobs_unresolved": sum(1 for item in results if item.status == "unresolved"),
        "jobs_failed": sum(1 for item in results if item.status == "failed"),
        "jobs_skipped": sum(1 for item in results if item.status == "skipped"),
        "jobs_missing": sum(1 for item in results if item.status == "missing"),
    }
