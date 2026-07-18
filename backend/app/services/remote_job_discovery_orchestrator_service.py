import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.jobs.enrichment.parsers.ashby_job_parser import AshbyJobParser
from app.jobs.enrichment.providers.ashby_public_job_client import AshbyPublicJobClient
from app.models.company import Company
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.schemas.remote_discovery import (
    RemoteDiscoverySourceResult,
    RemoteJobDiscoveryOrchestratorResult,
    RemoteJobDiscoveryPlanRead,
    RemoteRecommendationSummary,
)
from app.discovery.sources.hacker_news.schemas import HackerNewsDiscoveryRequest
from app.services.company_domain_enrichment_service import CompanyDomainEnrichmentService
from app.services.discovery_job_ingestion_service import DiscoveryJobIngestionService
from app.services.discovery_service import DiscoveryService
from app.services.himalayas_remote_job_discovery_service import HimalayasRemoteJobDiscoveryService
from app.services.job_batch_enrichment_service import JobBatchEnrichmentService
from app.services.job_matching_service import JobMatchingService
from app.services.remotive_remote_job_discovery_service import RemotiveRemoteJobDiscoveryService
from app.services.we_work_remotely_discovery_service import WeWorkRemotelyDiscoveryService
from app.utils.enums import CompanySource, JobEnrichmentStatus, JobStatus
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)

SOURCE_ORDER = ("himalayas", "we_work_remotely", "remotive")
ALL_SOURCE_ORDER = ("himalayas", "we_work_remotely", "remotive", "hacker_news", "ycombinator", "ashby")
SOURCE_LABELS = {
    "himalayas": "Himalayas",
    "we_work_remotely": "We Work Remotely",
    "remotive": "Remotive",
    "hacker_news": "Hacker News",
    "ycombinator": "Y Combinator",
    "ashby": "Ashby",
}


class RemoteJobDiscoveryOrchestratorService:
    def __init__(
        self,
        session: Session,
        *,
        himalayas_service: Any | None = None,
        we_work_remotely_service: Any | None = None,
        remotive_service: Any | None = None,
        discovery_service: DiscoveryService | None = None,
        domain_enrichment_service: CompanyDomainEnrichmentService | None = None,
        job_ingestion_service: DiscoveryJobIngestionService | None = None,
        job_enrichment_service: JobBatchEnrichmentService | None = None,
        ashby_client: AshbyPublicJobClient | None = None,
        ashby_parser: AshbyJobParser | None = None,
        matching_service: JobMatchingService | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.company_repository = CompanyRepository(session)
        self.job_repository = JobRepository(session)
        self.himalayas_service = himalayas_service or HimalayasRemoteJobDiscoveryService(session)
        self.we_work_remotely_service = we_work_remotely_service or WeWorkRemotelyDiscoveryService(session)
        self.remotive_service = remotive_service or RemotiveRemoteJobDiscoveryService(session)
        self.discovery_service = discovery_service or DiscoveryService(session)
        self.domain_enrichment_service = domain_enrichment_service or CompanyDomainEnrichmentService(session)
        self.job_ingestion_service = job_ingestion_service or DiscoveryJobIngestionService(session)
        self.job_enrichment_service = job_enrichment_service or JobBatchEnrichmentService(session)
        self.ashby_client = ashby_client or AshbyPublicJobClient()
        self.ashby_parser = ashby_parser or AshbyJobParser()
        self.matching_service = matching_service or JobMatchingService(session)

    def plan_remote_discovery(self) -> RemoteJobDiscoveryPlanRead:
        profile = self.matching_service.current_profile()
        enabled_sources = [source for source in SOURCE_ORDER if self._source_enabled(source)]
        disabled_sources = [source for source in SOURCE_ORDER if not self._source_enabled(source)]
        warnings: list[str] = []
        plans: dict[str, dict[str, Any] | None] = {source: None for source in ALL_SOURCE_ORDER}
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
            hacker_news=plans["hacker_news"],
            ycombinator=plans["ycombinator"],
            ashby=plans["ashby"],
            available_sources=_available_sources(),
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
                "hacker_news": {
                    "enabled": True,
                    "feeds": ["jobs"],
                    "limit": 100,
                    "lookback_days": 30,
                    "minimum_score": 0,
                    "include_items_without_website": True,
                    "enrich_domains": True,
                    "ingest_jobs": True,
                    "enrich_jobs": True,
                    "score_jobs": True,
                },
                "ycombinator": {
                    "enabled": True,
                    "max_pages": 5,
                    "remote_only": False,
                    "include_recent_only": True,
                    "lookback_days": 60,
                    "ingest_jobs": True,
                    "enrich_jobs": True,
                    "score_jobs": True,
                },
                "ashby": {
                    "enabled": True,
                    "board_slugs": [],
                    "max_jobs_per_board": 50,
                    "enrich_jobs": True,
                    "score_jobs": True,
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
        hacker_news_options: dict | None = None,
        ycombinator_options: dict | None = None,
        ashby_options: dict | None = None,
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
            "hacker_news": hacker_news_options or {},
            "ycombinator": ycombinator_options or {},
            "ashby": ashby_options or {},
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

        recommendation_job_ids = _job_ids_from_source_results(source_results) if sources is not None else []
        recommendation_scope = (
            "run_jobs"
            if sources is not None and recommendation_job_ids
            else "source_platform"
            if sources is not None
            else "global"
        )
        recommendations = self._top_recommendations(
            profile.id,
            job_ids=recommendation_job_ids if recommendation_job_ids else None,
            source_platforms=None if recommendation_job_ids or sources is None else _source_platforms_for_sources(selected),
        )
        logger.info("Remote discovery recommendations refreshed", extra={"profile_id": profile.id, "count": len(recommendations)})
        finished = datetime.now(timezone.utc)
        result = _build_result(
            profile_id=profile.id,
            planned=selected,
            source_results=source_results,
            recommendations=recommendations,
            recommendation_scope=recommendation_scope,
            recommendation_source_filter=selected if sources is not None else [],
            recommendation_job_ids_count=len(recommendation_job_ids),
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
            return [source for source in ALL_SOURCE_ORDER if source in sources]
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
            "hacker_news": True,
            "ycombinator": True,
            "ashby": True,
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
        if options.get("enabled") is False:
            return _skipped_source_result(source, f"{source}_disabled_by_request")
        if source == "hacker_news":
            return await self._run_hacker_news_source(
                options=options,
                score_after_ingestion=score_after_ingestion,
            )
        if source == "ycombinator":
            return _skipped_source_result(source, "yc_standalone_discovery_not_configured")
        if source == "ashby":
            if not options.get("board_slugs"):
                return _skipped_source_result(source, "ashby_board_slugs_required")
            return await self._run_ashby_source(
                options=options,
                score_after_ingestion=score_after_ingestion,
            )
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
        if source == "remotive":
            return await service.run_discovery(
                force=force,
                score_after_ingestion=score_after_ingestion,
                max_requests=options.get("max_requests"),
                limit_per_request=options.get("limit_per_request"),
            )
        raise AppError("REMOTE_DISCOVERY_UNSUPPORTED_SOURCE", f"Unsupported source: {source}")

    async def _run_hacker_news_source(
        self,
        *,
        options: dict[str, Any],
        score_after_ingestion: bool | None,
    ) -> dict[str, Any]:
        started = datetime.now(timezone.utc)
        request = HackerNewsDiscoveryRequest(
            feeds=options.get("feeds") or ["jobs"],
            limit=options.get("limit") or 100,
            lookback_days=options.get("lookback_days") or 30,
            minimum_score=options.get("minimum_score", 0),
            include_items_without_website=options.get("include_items_without_website", True),
            metadata={"remote_discovery_source": "hacker_news"},
        )
        discovery = await self.discovery_service.run_hacker_news_discovery(request)
        run = discovery.run
        warnings: list[str] = []
        domains_resolved = domains_unresolved = 0
        jobs_created = jobs_existing = jobs_skipped = jobs_failed = 0
        jobs_enriched = 0
        jobs_scored = 0
        jobs_not_enriched = 0
        scoring_distribution = {"eligible": 0, "stretch": 0, "uncertain": 0, "unsuitable": 0}
        job_ids: list[str] = []

        if options.get("enrich_domains", True):
            try:
                enrichment = await self.domain_enrichment_service.enrich_discovery_run(run.id)
                domains_resolved = enrichment.candidates_resolved
                domains_unresolved = enrichment.candidates_unresolved
                warnings.extend(
                    result.message
                    for result in enrichment.results
                    if result.decision and str(result.decision).endswith("UNRESOLVED")
                )
            except Exception as exc:
                self.session.rollback()
                warnings.append(f"domain_enrichment_failed:{_safe_error(exc)}")

        if options.get("ingest_jobs", True):
            try:
                ingestion = self.job_ingestion_service.ingest_discovery_run(run.id)
                jobs_created = ingestion.jobs_created
                jobs_existing = ingestion.jobs_existing
                jobs_skipped = ingestion.candidates_skipped
                jobs_failed = ingestion.candidates_failed
                job_ids = [result.job_id for result in ingestion.results if result.job_id]
            except Exception as exc:
                self.session.rollback()
                warnings.append(f"job_ingestion_failed:{_safe_error(exc)}")

        if job_ids and options.get("enrich_jobs", True):
            try:
                enriched = await self.job_enrichment_service.enrich_jobs(
                    job_ids=job_ids,
                    limit=len(job_ids),
                    force=True,
                    include_failed=True,
                )
                jobs_enriched = enriched.jobs_enriched + enriched.jobs_partially_enriched
                if enriched.jobs_unresolved or enriched.jobs_failed:
                    jobs_not_enriched = enriched.jobs_unresolved + enriched.jobs_failed
                    warnings.append(f"{jobs_not_enriched} of {len(job_ids)} Hacker News jobs were not enriched")
            except Exception as exc:
                self.session.rollback()
                warnings.append(f"job_enrichment_failed:{_safe_error(exc)}")

        if job_ids and (score_after_ingestion or options.get("score_jobs", True)):
            try:
                profile = self.matching_service.current_profile()
                scored = self.matching_service.score_jobs(profile.id, job_ids=job_ids, force=True)
                jobs_scored = scored.jobs_scored
                scoring_distribution = {
                    "eligible": getattr(scored, "eligible", 0),
                    "stretch": getattr(scored, "stretch", 0),
                    "uncertain": getattr(scored, "uncertain", 0),
                    "unsuitable": getattr(scored, "unsuitable", 0),
                }
                if scored.jobs_failed:
                    warnings.append("some_jobs_not_scored")
            except Exception as exc:
                self.session.rollback()
                warnings.append(f"job_scoring_failed:{_safe_error(exc)}")

        hn_job_quality = self._hacker_news_job_quality(job_ids)
        finished = datetime.now(timezone.utc)
        return {
            "source": "hacker_news",
            "status": "partial" if warnings else "succeeded",
            "reason": "hacker_news_completed_with_warnings" if warnings else None,
            "discovery_run_id": run.id,
            "started_at": started,
            "finished_at": finished,
            "duration_ms": int((finished - started).total_seconds() * 1000),
            "provider_records_seen": discovery.fetched_item_count,
            "fetched_item_count": discovery.fetched_item_count,
            "skipped_item_count": discovery.skipped_item_count,
            "candidates_found": run.candidates_found,
            "candidates_created": run.candidates_normalized,
            "candidates_normalized": run.candidates_normalized,
            "candidates_deferred": run.candidates_deferred,
            "candidates_rejected": run.candidates_rejected,
            "candidates_failed": run.candidates_failed,
            "companies_created": run.companies_created,
            "companies_matched": run.companies_matched,
            "domains_resolved": domains_resolved,
            "domains_unresolved": domains_unresolved,
            "jobs_created": jobs_created,
            "jobs_existing": jobs_existing,
            "jobs_updated": 0,
            "jobs_skipped": jobs_skipped,
            "jobs_failed": jobs_failed,
            "jobs_enriched": jobs_enriched,
            "jobs_scored": jobs_scored,
            "warnings": warnings,
            "diagnostics": {
                "phases": ["discover", "enrich_domains", "ingest_jobs", "enrich_jobs", "score_jobs"],
                "job_ids": job_ids[:25],
                "h_n_jobs_scored_eligible": scoring_distribution["eligible"],
                "h_n_jobs_scored_stretch": scoring_distribution["stretch"],
                "h_n_jobs_scored_uncertain": scoring_distribution["uncertain"],
                "h_n_jobs_scored_unsuitable": scoring_distribution["unsuitable"],
                "h_n_jobs_remaining_open_roles": hn_job_quality["remaining_open_roles"],
                "h_n_jobs_remaining_remote_unknown": hn_job_quality["remaining_remote_unknown"],
                "h_n_jobs_not_enriched": jobs_not_enriched or hn_job_quality["not_enriched"],
                "jobs_not_enriched": jobs_not_enriched,
                "jobs_remaining_open_roles": hn_job_quality["remaining_open_roles"],
                "jobs_remote_unknown": hn_job_quality["remaining_remote_unknown"],
            },
        }

    async def _run_ashby_source(
        self,
        *,
        options: dict[str, Any],
        score_after_ingestion: bool | None,
    ) -> dict[str, Any]:
        started = datetime.now(timezone.utc)
        board_slugs = _unique_slug_list(options.get("board_slugs") or [])
        max_jobs_per_board = options.get("max_jobs_per_board") or 50
        warnings: list[str] = []
        job_ids: list[str] = []
        boards_resolved = 0
        jobs_seen = jobs_created = jobs_existing = jobs_updated = jobs_failed = 0
        company_domain_missing = 0
        unresolved = 0

        for board_slug in board_slugs:
            response = await self.ashby_client.list_published_jobs(board_slug)
            if response.reason:
                warnings.append(f"{board_slug}:{response.reason}")
                unresolved += 1
                continue
            boards_resolved += 1
            postings = [posting for posting in response.jobs if posting.id and posting.title][:max_jobs_per_board]
            jobs_seen += len(postings)
            company = self._company_for_ashby_board(board_slug)
            company_domain_missing += 1
            warnings.append(f"{board_slug}:ashby_company_domain_missing")
            for posting in postings:
                try:
                    parsed = self.ashby_parser.parse_posting(posting, board_slug=board_slug)
                    job_url = _field_value(parsed.job_url) or parsed.canonical_url
                    if not parsed.success or not job_url:
                        jobs_failed += 1
                        warnings.append(f"{board_slug}:{posting.id or posting.raw_index}:ashby_job_data_missing")
                        continue
                    updates = _ashby_job_updates(parsed)
                    existing = self.job_repository.get_by_company_and_url(company.id, job_url)
                    if existing is None:
                        job = self.job_repository.create_job(
                            Job(
                                company_id=company.id,
                                title=updates["title"],
                                normalized_title=updates.get("normalized_title"),
                                description=updates.get("description"),
                                location=updates.get("location"),
                                remote_type=updates.get("remote_type"),
                                role_category=updates.get("role_category"),
                                experience_min=updates.get("experience_min"),
                                experience_max=updates.get("experience_max"),
                                salary_min=updates.get("salary_min"),
                                salary_max=updates.get("salary_max"),
                                salary_currency=updates.get("salary_currency"),
                                job_url=job_url,
                                source_platform="ashby",
                                status=JobStatus.ACTIVE,
                                first_seen_at=_field_value(parsed.published_at) or datetime.now(timezone.utc),
                                last_seen_at=datetime.now(timezone.utc),
                                seniority=updates.get("seniority"),
                                employment_type=updates.get("employment_type"),
                                apply_url=updates.get("apply_url"),
                                published_at=updates.get("published_at"),
                                salary_text=updates.get("salary_text"),
                                equity_mentioned=updates.get("equity_mentioned"),
                                required_skills_json=updates.get("required_skills_json"),
                                preferred_skills_json=updates.get("preferred_skills_json"),
                                technologies_json=updates.get("technologies_json"),
                                enrichment_status=JobEnrichmentStatus.ENRICHED.value,
                                enrichment_confidence=updates.get("enrichment_confidence"),
                                enriched_at=datetime.now(timezone.utc),
                                last_verified_at=datetime.now(timezone.utc),
                            )
                        )
                        jobs_created += 1
                    else:
                        update_values = {key: value for key, value in updates.items() if value is not None}
                        update_values["last_seen_at"] = datetime.now(timezone.utc)
                        self.job_repository.update_job(existing, {"last_seen_at": update_values.pop("last_seen_at")})
                        job = self.job_repository.update_enrichment_fields(existing.id, update_values)
                        jobs_existing += 1
                        jobs_updated += 1
                    job_ids.append(job.id)
                except Exception as exc:
                    self.session.rollback()
                    jobs_failed += 1
                    warnings.append(f"{board_slug}:{posting.id or posting.raw_index}:{_safe_error(exc)}")

        jobs_scored = 0
        if job_ids and (score_after_ingestion or options.get("score_jobs", True)):
            try:
                profile = self.matching_service.current_profile()
                scored = self.matching_service.score_jobs(profile.id, job_ids=job_ids, force=True)
                jobs_scored = scored.jobs_scored
                if scored.jobs_failed:
                    warnings.append("some_ashby_jobs_not_scored")
            except Exception as exc:
                self.session.rollback()
                warnings.append(f"ashby_job_scoring_failed:{_safe_error(exc)}")

        finished = datetime.now(timezone.utc)
        return {
            "source": "ashby",
            "status": "partial" if warnings else "succeeded",
            "reason": "ashby_completed_with_warnings" if warnings else None,
            "started_at": started,
            "finished_at": finished,
            "duration_ms": int((finished - started).total_seconds() * 1000),
            "provider_records_seen": jobs_seen,
            "unique_records": len(set(job_ids)),
            "jobs_created": jobs_created,
            "jobs_existing": jobs_existing,
            "jobs_updated": jobs_updated,
            "jobs_failed": jobs_failed,
            "jobs_enriched": jobs_created + jobs_updated,
            "jobs_scored": jobs_scored,
            "warnings": warnings,
            "diagnostics": {
                "ashby_links_detected": len(board_slugs),
                "ashby_boards_resolved": boards_resolved,
                "ashby_jobs_matched": jobs_created + jobs_existing,
                "ashby_jobs_expanded": jobs_seen,
                "ashby_jobs_enriched": jobs_created + jobs_updated,
                "ashby_company_domain_missing_count": company_domain_missing,
                "ashby_board_slug_missing_count": 0,
                "ashby_job_not_found_count": jobs_failed,
                "ashby_unresolved_count": unresolved,
                "job_ids": job_ids[:25],
            },
        }

    def _company_for_ashby_board(self, board_slug: str) -> Company:
        normalized_domain = f"ashby:{board_slug.lower()}"
        existing = self.company_repository.get_by_domain(normalized_domain)
        if existing is not None:
            return existing
        return self.company_repository.create_company(
            Company(
                name=_name_from_slug(board_slug),
                website_url=None,
                normalized_domain=normalized_domain,
                description=None,
                country=None,
                city=None,
                source=CompanySource.OTHER,
            )
        )

    def _hacker_news_job_quality(self, job_ids: list[str]) -> dict[str, int]:
        jobs: list[Job] = []
        for job_id in job_ids:
            try:
                job = self.job_repository.get_by_id(job_id)
            except Exception:
                continue
            if job is not None:
                jobs.append(job)
        return {
            "remaining_open_roles": sum(1 for job in jobs if (job.title or "").strip().lower() == "open roles"),
            "remaining_remote_unknown": sum(1 for job in jobs if str(job.remote_type or "") == "unknown"),
            "not_enriched": sum(1 for job in jobs if job.enrichment_status == JobEnrichmentStatus.NOT_ENRICHED.value),
        }

    def _top_recommendations(
        self,
        profile_id: str,
        *,
        job_ids: list[str] | None = None,
        source_platforms: list[str] | None = None,
    ) -> list[RemoteRecommendationSummary]:
        matches = self.matching_service.list_matches(
            profile_id,
            job_ids=job_ids,
            source_platforms=source_platforms,
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
        jobs_skipped=data.get("jobs_skipped", 0) or 0,
        jobs_enriched=data.get("jobs_enriched", 0) or 0,
        candidates_created=data.get("candidates_created", 0) or 0,
        candidates_existing=data.get("candidates_existing", 0) or 0,
        candidates_rejected=data.get("candidates_rejected", 0) or 0,
        candidates_found=data.get("candidates_found", 0) or 0,
        candidates_normalized=data.get("candidates_normalized", 0) or 0,
        candidates_deferred=data.get("candidates_deferred", 0) or 0,
        candidates_failed=data.get("candidates_failed", 0) or 0,
        companies_created=data.get("companies_created", 0) or 0,
        companies_matched=data.get("companies_matched", 0) or 0,
        domains_resolved=data.get("domains_resolved", 0) or 0,
        domains_unresolved=data.get("domains_unresolved", 0) or 0,
        provider_records_seen=provider_records_seen,
        unique_records=unique_records,
        accepted_jobs_count=len(data.get("accepted_jobs") or []),
        rejected_samples_count=len(data.get("rejected_samples") or []),
        accepted_jobs=accepted_jobs,
        rejected_samples=rejected_samples,
        warnings=list(data.get("warnings") or []),
        diagnostics=dict(data.get("diagnostics") or {}),
    )


def _build_result(
    *,
    profile_id: str,
    planned: list[str],
    source_results: list[RemoteDiscoverySourceResult],
    recommendations: list[RemoteRecommendationSummary],
    recommendation_scope: str,
    recommendation_source_filter: list[str],
    recommendation_job_ids_count: int,
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
        recommendation_scope=recommendation_scope,
        recommendation_source_filter=recommendation_source_filter,
        recommendation_job_ids_count=recommendation_job_ids_count,
        started_at=started,
        finished_at=finished,
        duration_ms=int((finished - started).total_seconds() * 1000),
        warnings=warnings,
    )


def _skipped_source_result(source: str, reason: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "source": source,
        "status": "skipped",
        "reason": reason,
        "started_at": now,
        "finished_at": now,
        "duration_ms": 0,
        "warnings": [reason],
        "diagnostics": {"source": source, "reason": reason},
    }


def _job_ids_from_source_results(source_results: list[RemoteDiscoverySourceResult]) -> list[str]:
    job_ids: list[str] = []
    for result in source_results:
        for value in result.diagnostics.get("job_ids") or []:
            if value and value not in job_ids:
                job_ids.append(str(value))
        for item in result.accepted_jobs:
            value = item.get("job_id") if isinstance(item, dict) else None
            if value and value not in job_ids:
                job_ids.append(str(value))
    return job_ids


def _source_platforms_for_sources(sources: list[str]) -> list[str]:
    mapping = {
        "himalayas": "himalayas",
        "we_work_remotely": "we_work_remotely",
        "remotive": "remotive",
        "hacker_news": "hacker_news",
        "ycombinator": "ycombinator",
        "ashby": "ashby",
    }
    return [mapping[source] for source in sources if source in mapping]


def _available_sources() -> list[dict[str, Any]]:
    return [
        {
            "source": "himalayas",
            "enabled_by_default": True,
            "description": "Targeted remote job discovery from Himalayas.",
            "expected_behavior": "Creates, updates, and scores remote jobs.",
            "required_options": [],
        },
        {
            "source": "we_work_remotely",
            "enabled_by_default": True,
            "description": "Targeted RSS job discovery from We Work Remotely.",
            "expected_behavior": "Creates, updates, and scores remote jobs.",
            "required_options": [],
        },
        {
            "source": "remotive",
            "enabled_by_default": True,
            "description": "Targeted Remotive API remote job discovery.",
            "expected_behavior": "Creates, updates, and scores remote jobs.",
            "required_options": [],
        },
        {
            "source": "hacker_news",
            "enabled_by_default": False,
            "description": "Candidate-first Hacker News Who is Hiring discovery.",
            "expected_behavior": "Fetches HN candidates, resolves company domains, ingests jobs, enriches jobs, then scores them.",
            "required_options": [],
        },
        {
            "source": "ycombinator",
            "enabled_by_default": False,
            "description": "Y Combinator job discovery and enrichment source.",
            "expected_behavior": "Accepted by the unified runner; exact YC job enrichment is used when YC URLs are ingested.",
            "required_options": [],
        },
        {
            "source": "ashby",
            "enabled_by_default": False,
            "description": "Ashby job-board resolver/enrichment source with optional board slugs.",
            "expected_behavior": "Accepted by the unified runner; Ashby links are enriched from HN/YC jobs. Standalone board discovery requires board_slugs.",
            "required_options": ["board_slugs"],
        },
    ]


def _field_value(field: Any) -> Any:
    return getattr(field, "value", None) if field is not None else None


def _ashby_job_updates(parsed: Any) -> dict[str, Any]:
    title = _field_value(parsed.title) or "Untitled Ashby Job"
    return {
        "title": title,
        "normalized_title": normalize_title(title) or title.lower(),
        "description": _field_value(parsed.description),
        "role_category": _field_value(parsed.role_category),
        "seniority": _field_value(parsed.seniority),
        "location": _field_value(parsed.location),
        "remote_type": _field_value(parsed.remote_type),
        "employment_type": _field_value(parsed.employment_type),
        "experience_min": _field_value(parsed.experience_min),
        "experience_max": _field_value(parsed.experience_max),
        "salary_min": _field_value(parsed.salary_min),
        "salary_max": _field_value(parsed.salary_max),
        "salary_currency": _field_value(parsed.salary_currency),
        "salary_text": _field_value(parsed.salary_text),
        "equity_mentioned": _field_value(parsed.equity_mentioned),
        "job_url": _field_value(parsed.job_url) or parsed.canonical_url,
        "apply_url": _field_value(parsed.apply_url),
        "published_at": _field_value(parsed.published_at),
        "required_skills_json": _field_value(parsed.required_skills),
        "preferred_skills_json": _field_value(parsed.preferred_skills),
        "technologies_json": _field_value(parsed.technologies),
        "enrichment_status": JobEnrichmentStatus.ENRICHED.value,
        "enrichment_confidence": parsed.evidence.get("overall_confidence"),
        "last_verified_at": datetime.now(timezone.utc),
        "enriched_at": datetime.now(timezone.utc),
    }


def _unique_slug_list(values: list[Any]) -> list[str]:
    slugs: list[str] = []
    for value in values:
        slug = str(value or "").strip()
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def _name_from_slug(value: str) -> str:
    words = [part for part in value.replace("_", "-").split("-") if part]
    return " ".join(part.capitalize() for part in words) or value


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    return exc.__class__.__name__
