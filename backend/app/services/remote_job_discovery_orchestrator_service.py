import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.schemas.remote_discovery import (
    RemoteDiscoverySourceResult,
    RemoteJobDiscoveryOrchestratorResult,
    RemoteJobDiscoveryPlanRead,
    RemoteRecommendationSummary,
)
from app.services.himalayas_remote_job_discovery_service import HimalayasRemoteJobDiscoveryService
from app.services.job_matching_service import JobMatchingService
from app.services.remotive_remote_job_discovery_service import RemotiveRemoteJobDiscoveryService
from app.services.we_work_remotely_discovery_service import WeWorkRemotelyDiscoveryService

logger = logging.getLogger(__name__)

SOURCE_ORDER = ("himalayas", "we_work_remotely", "remotive")
SOURCE_LABELS = {
    "himalayas": "Himalayas",
    "we_work_remotely": "We Work Remotely",
    "remotive": "Remotive",
}


class RemoteJobDiscoveryOrchestratorService:
    def __init__(
        self,
        session: Session,
        *,
        himalayas_service: Any | None = None,
        we_work_remotely_service: Any | None = None,
        remotive_service: Any | None = None,
        matching_service: JobMatchingService | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.himalayas_service = himalayas_service or HimalayasRemoteJobDiscoveryService(session)
        self.we_work_remotely_service = we_work_remotely_service or WeWorkRemotelyDiscoveryService(session)
        self.remotive_service = remotive_service or RemotiveRemoteJobDiscoveryService(session)
        self.matching_service = matching_service or JobMatchingService(session)

    def plan_remote_discovery(self) -> RemoteJobDiscoveryPlanRead:
        profile = self.matching_service.current_profile()
        enabled_sources = [source for source in SOURCE_ORDER if self._source_enabled(source)]
        disabled_sources = [source for source in SOURCE_ORDER if not self._source_enabled(source)]
        warnings: list[str] = []
        plans: dict[str, dict[str, Any] | None] = {source: None for source in SOURCE_ORDER}
        cooldowns: dict[str, dict[str, Any]] = {}

        for source in SOURCE_ORDER:
            if not self._source_enabled(source):
                cooldowns[source] = {"enabled": False, "cooldown_active": False}
                continue
            try:
                plan = self._source_service(source).query_plan_result()
                cooldown = self._cooldown_status(source, profile.id, plan)
                plans[source] = plan
                cooldowns[source] = cooldown
            except NotFoundError:
                raise
            except Exception as exc:
                logger.info("Remote discovery plan source failed", extra={"source": source, "error": exc.__class__.__name__})
                warnings.append(f"{source}_plan_unavailable")
                cooldowns[source] = {"enabled": True, "cooldown_active": False, "error": _safe_error(exc)}

        return RemoteJobDiscoveryPlanRead(
            profile_id=profile.id,
            enabled_sources=enabled_sources,
            disabled_sources=disabled_sources,
            cooldowns=cooldowns,
            himalayas=plans["himalayas"],
            we_work_remotely=plans["we_work_remotely"],
            remotive=plans["remotive"],
            recommended_defaults={
                "force": False,
                "sources": enabled_sources,
                "score_after_ingestion": True,
                "himalayas": {
                    "max_queries": self.settings.HIMALAYAS_MAX_QUERIES_PER_RUN,
                    "max_pages_per_query": self.settings.HIMALAYAS_MAX_PAGES_PER_QUERY,
                },
                "we_work_remotely": {
                    "include_all_other": self.settings.WWR_INCLUDE_ALL_OTHER_FEED,
                    "max_items_per_feed": self.settings.WWR_MAX_ITEMS_PER_FEED,
                },
                "remotive": {
                    "max_requests": self.settings.REMOTIVE_MAX_REQUESTS_PER_RUN,
                    "limit_per_request": self.settings.REMOTIVE_MAX_JOBS_PER_REQUEST,
                },
            },
            warnings=warnings,
        )

    async def run_remote_discovery(
        self,
        *,
        force: bool = False,
        sources: list[str] | None = None,
        score_after_ingestion: bool | None = True,
        include_himalayas: bool = True,
        include_we_work_remotely: bool = True,
        include_remotive: bool = True,
        himalayas_options: dict | None = None,
        we_work_remotely_options: dict | None = None,
        remotive_options: dict | None = None,
    ) -> RemoteJobDiscoveryOrchestratorResult:
        started = datetime.now(timezone.utc)
        profile = self.matching_service.current_profile()
        selected = self._selected_sources(
            sources=sources,
            include_himalayas=include_himalayas,
            include_we_work_remotely=include_we_work_remotely,
            include_remotive=include_remotive,
        )
        if not selected:
            raise AppError("REMOTE_DISCOVERY_NO_SOURCES", "No remote discovery sources selected", status_code=503)

        logger.info("Unified remote discovery requested", extra={"profile_id": profile.id, "sources": selected, "force": force})
        source_results: list[RemoteDiscoverySourceResult] = []
        options = {
            "himalayas": himalayas_options or {},
            "we_work_remotely": we_work_remotely_options or {},
            "remotive": remotive_options or {},
        }

        for source in selected:
            logger.info("Remote discovery source planned", extra={"source": source})
            if not self._source_enabled(source):
                now = datetime.now(timezone.utc)
                logger.info("Remote discovery source skipped", extra={"source": source, "reason": "source_disabled"})
                source_results.append(
                    RemoteDiscoverySourceResult(
                        source=source,
                        status="disabled",
                        reason=f"{source}_discovery_disabled",
                        started_at=now,
                        finished_at=now,
                        duration_ms=0,
                    )
                )
                continue
            try:
                logger.info("Remote discovery source started", extra={"source": source})
                result = await self._run_source(
                    source,
                    force=force,
                    score_after_ingestion=score_after_ingestion,
                    options=options[source],
                )
                normalized = _normalize_source_result(source, result)
                source_results.append(normalized)
                if normalized.status == "skipped":
                    logger.info("Remote discovery source skipped", extra={"source": source, "reason": normalized.reason})
                else:
                    logger.info("Remote discovery source completed", extra={"source": source, "status": normalized.status})
            except NotFoundError:
                raise
            except Exception as exc:
                self.session.rollback()
                finished = datetime.now(timezone.utc)
                logger.info("Remote discovery source failed", extra={"source": source, "error": exc.__class__.__name__})
                source_results.append(
                    RemoteDiscoverySourceResult(
                        source=source,
                        status="failed",
                        reason=f"{source}_provider_failed",
                        error=_safe_error(exc),
                        started_at=finished,
                        finished_at=finished,
                        duration_ms=0,
                    )
                )

        recommendations = self._top_recommendations(profile.id)
        logger.info("Remote discovery recommendations refreshed", extra={"profile_id": profile.id, "count": len(recommendations)})
        finished = datetime.now(timezone.utc)
        result = _build_result(
            profile_id=profile.id,
            planned=selected,
            source_results=source_results,
            recommendations=recommendations,
            started=started,
            finished=finished,
        )
        logger.info("Remote discovery orchestrator completed", extra={"status": result.status, "reason": result.reason})
        if result.status == "partial":
            logger.info("Remote discovery orchestrator partial", extra={"sources_failed": result.sources_failed})
        if result.status == "failed":
            logger.info("Remote discovery orchestrator failed", extra={"reason": result.reason})
        return result

    def _selected_sources(
        self,
        *,
        sources: list[str] | None,
        include_himalayas: bool,
        include_we_work_remotely: bool,
        include_remotive: bool,
    ) -> list[str]:
        if sources is not None:
            return [source for source in SOURCE_ORDER if source in sources]
        included = {
            "himalayas": include_himalayas,
            "we_work_remotely": include_we_work_remotely,
            "remotive": include_remotive,
        }
        return [source for source in SOURCE_ORDER if included[source] and self._source_enabled(source)]

    def _source_enabled(self, source: str) -> bool:
        return {
            "himalayas": self.settings.HIMALAYAS_DISCOVERY_ENABLED,
            "we_work_remotely": self.settings.WWR_DISCOVERY_ENABLED,
            "remotive": self.settings.REMOTIVE_DISCOVERY_ENABLED,
        }[source]

    def _source_service(self, source: str) -> Any:
        return {
            "himalayas": self.himalayas_service,
            "we_work_remotely": self.we_work_remotely_service,
            "remotive": self.remotive_service,
        }[source]

    def _cooldown_status(self, source: str, profile_id: str, plan: dict[str, Any]) -> dict[str, Any]:
        if "cooldown_active" in plan:
            return {
                "enabled": True,
                "cooldown_active": bool(plan.get("cooldown_active", False)),
                "previous_run_id": plan.get("previous_run_id"),
                "next_eligible_at": plan.get("next_eligible_at"),
            }
        if source == "himalayas" and hasattr(self.himalayas_service, "_cooldown_result"):
            cooldown = self.himalayas_service._cooldown_result(profile_id, datetime.now(timezone.utc))
            return {
                "enabled": True,
                "cooldown_active": cooldown is not None,
                "previous_run_id": getattr(cooldown, "previous_run_id", None),
                "next_eligible_at": getattr(cooldown, "next_eligible_at", None),
            }
        return {"enabled": True, "cooldown_active": False}

    async def _run_source(self, source: str, *, force: bool, score_after_ingestion: bool | None, options: dict[str, Any]) -> Any:
        service = self._source_service(source)
        if source == "himalayas":
            return await service.run_discovery(
                force=force,
                score_after_ingestion=score_after_ingestion,
                max_queries=options.get("max_queries"),
                max_pages_per_query=options.get("max_pages_per_query"),
            )
        if source == "we_work_remotely":
            return await service.run_discovery(
                force=force,
                score_after_ingestion=score_after_ingestion,
                include_all_other=options.get("include_all_other"),
                max_items_per_feed=options.get("max_items_per_feed"),
            )
        return await service.run_discovery(
            force=force,
            score_after_ingestion=score_after_ingestion,
            max_requests=options.get("max_requests"),
            limit_per_request=options.get("limit_per_request"),
        )

    def _top_recommendations(self, profile_id: str) -> list[RemoteRecommendationSummary]:
        matches = self.matching_service.list_matches(
            profile_id,
            include_unsuitable=False,
            include_remote_unknown=False,
            limit=10,
            order_by="recommended",
        )
        summaries: list[RemoteRecommendationSummary] = []
        for match in matches:
            job = match.job
            company = getattr(job, "company", None)
            summaries.append(
                RemoteRecommendationSummary(
                    job_id=job.id,
                    company_name=getattr(company, "name", None),
                    title=job.title,
                    remote_eligibility=match.remote_eligibility,
                    match_tier=match.match_tier,
                    eligibility_status=match.eligibility_status,
                    total_score=match.total_score,
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    salary_currency=job.salary_currency,
                    job_url=job.job_url,
                    apply_url=job.apply_url,
                    eligibility_reason=match.eligibility_reason,
                )
            )
        return summaries


def _normalize_source_result(source: str, result: Any) -> RemoteDiscoverySourceResult:
    data = result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)
    accepted_jobs = list(data.get("accepted_jobs") or [])[:25]
    rejected_samples = list(data.get("rejected_samples") or [])[:10]
    provider_records_seen = data.get("provider_records_seen", data.get("feed_items_seen", 0)) or 0
    unique_records = data.get("unique_records", data.get("unique_items", 0)) or 0
    return RemoteDiscoverySourceResult(
        source=source,
        status=data.get("status") or "failed",
        reason=data.get("reason"),
        discovery_run_id=data.get("discovery_run_id"),
        started_at=data["started_at"],
        finished_at=data["finished_at"],
        duration_ms=data.get("duration_ms", 0) or 0,
        jobs_created=data.get("jobs_created", 0) or 0,
        jobs_existing=data.get("jobs_existing", 0) or 0,
        jobs_updated=data.get("jobs_updated", 0) or 0,
        jobs_scored=data.get("jobs_scored", 0) or 0,
        jobs_failed=data.get("jobs_failed", 0) or 0,
        candidates_created=data.get("candidates_created", 0) or 0,
        candidates_existing=data.get("candidates_existing", 0) or 0,
        candidates_rejected=data.get("candidates_rejected", 0) or 0,
        provider_records_seen=provider_records_seen,
        unique_records=unique_records,
        accepted_jobs_count=len(data.get("accepted_jobs") or []),
        rejected_samples_count=len(data.get("rejected_samples") or []),
        accepted_jobs=accepted_jobs,
        rejected_samples=rejected_samples,
        warnings=list(data.get("warnings") or []),
    )


def _build_result(
    *,
    profile_id: str,
    planned: list[str],
    source_results: list[RemoteDiscoverySourceResult],
    recommendations: list[RemoteRecommendationSummary],
    started: datetime,
    finished: datetime,
) -> RemoteJobDiscoveryOrchestratorResult:
    failed = [item for item in source_results if item.status == "failed"]
    skipped = [item for item in source_results if item.status in {"skipped", "disabled"}]
    completed = [item for item in source_results if item.status not in {"failed", "skipped", "disabled"}]
    if completed and failed:
        status = "partial"
        reason = "some_sources_failed"
    elif failed and len(failed) == len(source_results):
        status = "failed"
        reason = "all_sources_failed"
    elif source_results and len(skipped) == len(source_results):
        status = "skipped"
        if all(item.status == "disabled" for item in skipped):
            reason = "no_sources_enabled"
        else:
            reason = "provider_cooldowns_active"
    else:
        status = "succeeded"
        reason = None

    warnings = [warning for result in source_results for warning in result.warnings]
    return RemoteJobDiscoveryOrchestratorResult(
        status=status,
        reason=reason,
        profile_id=profile_id,
        sources_planned=planned,
        sources_completed=len(completed),
        sources_failed=len(failed),
        sources_skipped=len(skipped),
        total_provider_records_seen=sum(item.provider_records_seen for item in source_results),
        total_unique_records=sum(item.unique_records for item in source_results),
        total_candidates_created=sum(item.candidates_created for item in source_results),
        total_candidates_existing=sum(item.candidates_existing for item in source_results),
        total_candidates_rejected=sum(item.candidates_rejected for item in source_results),
        total_jobs_created=sum(item.jobs_created for item in source_results),
        total_jobs_existing=sum(item.jobs_existing for item in source_results),
        total_jobs_updated=sum(item.jobs_updated for item in source_results),
        total_jobs_scored=sum(item.jobs_scored for item in source_results),
        total_jobs_failed=sum(item.jobs_failed for item in source_results),
        source_results=source_results,
        top_recommendations=recommendations,
        started_at=started,
        finished_at=finished,
        duration_ms=int((finished - started).total_seconds() * 1000),
        warnings=warnings,
    )


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    return exc.__class__.__name__
