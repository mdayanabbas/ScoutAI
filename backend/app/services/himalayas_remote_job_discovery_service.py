import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.discovery.sources.himalayas.client import HimalayasRemoteJobsClient
from app.discovery.sources.himalayas.constants import (
    HIMALAYAS_ATTRIBUTION_LABEL,
    HIMALAYAS_HOME_URL,
    HIMALAYAS_PROVIDER,
    HIMALAYAS_REMOTE_JOBS_SOURCE,
)
from app.discovery.sources.himalayas.models import HimalayasJobPayload
from app.discovery.sources.himalayas.parser import HimalayasJobParser, ParsedHimalayasJob
from app.discovery.sources.himalayas.query_planner import HimalayasQueryPass, HimalayasTargetedQueryPlanner
from app.jobs.job_source_detector import normalize_job_url
from app.models.company import Company
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.discovery_evidence import DiscoveryEvidence
from app.models.discovery_run import DiscoveryRun
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.discovery_candidate_repository import DiscoveryCandidateRepository
from app.repositories.discovery_evidence_repository import DiscoveryEvidenceRepository
from app.repositories.discovery_run_repository import DiscoveryRunRepository
from app.repositories.job_discovery_link_repository import JobDiscoveryLinkRepository
from app.repositories.job_matching_profile_repository import JobMatchingProfileRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import UserProfileRepository
from app.schemas.himalayas_discovery import (
    HimalayasAcceptedJobSummary,
    HimalayasDiscoveryResult,
    HimalayasQueryResult,
    HimalayasRejectedCandidateSummary,
)
from app.services.job_matching_service import JobMatchingService
from app.utils.enums import (
    CompanySource,
    CompanyStage,
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
    JobEnrichmentStatus,
    JobStatus,
)

logger = logging.getLogger(__name__)

REMOTE_ORDER = {
    "work_from_anywhere": 0,
    "remote_india_eligible": 1,
    "remote_global_unspecified": 2,
    "remote_eligibility_unclear": 3,
}
TIER_ORDER = {"best_match": 0, "strong_match": 1, "worth_checking": 2, "stretch": 3, "unsuitable": 4}


class HimalayasRemoteJobDiscoveryService:
    def __init__(
        self,
        session: Session,
        *,
        client: HimalayasRemoteJobsClient | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.client = client or HimalayasRemoteJobsClient()
        self.query_planner = HimalayasTargetedQueryPlanner()
        self.parser = HimalayasJobParser()
        self.run_repository = DiscoveryRunRepository(session)
        self.candidate_repository = DiscoveryCandidateRepository(session)
        self.evidence_repository = DiscoveryEvidenceRepository(session)
        self.company_repository = CompanyRepository(session)
        self.job_repository = JobRepository(session)
        self.link_repository = JobDiscoveryLinkRepository(session)
        self.user_profile_repository = UserProfileRepository(session)
        self.profile_repository = JobMatchingProfileRepository(session)

    def query_plan_result(self) -> dict[str, Any]:
        profile = self._current_profile()
        max_queries = self.settings.HIMALAYAS_MAX_QUERIES_PER_RUN
        plan = self.query_planner.build_plan(profile, max_queries=max_queries)
        return {
            "current_profile_target_titles": list(profile.target_titles_json or []),
            "normalized_queries": plan.queries,
            "worldwide_passes": [vars(item) for item in plan.passes if item.query_type == "worldwide"],
            "india_passes": [vars(item) for item in plan.passes if item.query_type == "india"],
            "query_count": len(plan.passes),
            "generated_from_profile": plan.generated_from_profile,
            "warnings": plan.warnings,
        }

    async def run_discovery(
        self,
        *,
        force: bool = False,
        max_queries: int | None = None,
        max_pages_per_query: int | None = None,
        score_after_ingestion: bool | None = None,
    ) -> HimalayasDiscoveryResult:
        started = datetime.now(timezone.utc)
        if not self.settings.HIMALAYAS_DISCOVERY_ENABLED:
            raise AppError("HIMALAYAS_DISCOVERY_DISABLED", "Himalayas discovery is disabled", status_code=503)
        profile = self._current_profile()
        cooldown = self._cooldown_result(profile.id, started) if not force else None
        if cooldown is not None:
            return cooldown

        query_limit = min(max_queries or self.settings.HIMALAYAS_MAX_QUERIES_PER_RUN, self.settings.HIMALAYAS_MAX_QUERIES_PER_RUN)
        page_limit = min(max_pages_per_query or self.settings.HIMALAYAS_MAX_PAGES_PER_QUERY, self.settings.HIMALAYAS_MAX_PAGES_PER_QUERY)
        should_score = self.settings.HIMALAYAS_SCORE_AFTER_INGESTION if score_after_ingestion is None else score_after_ingestion
        plan = self.query_planner.build_plan(profile, max_queries=query_limit)
        run = self.run_repository.create_run(
            DiscoveryRun(
                source=DiscoverySource.HIMALAYAS,
                status=DiscoveryRunStatus.PENDING,
                candidates_found=0,
                candidates_normalized=0,
                companies_created=0,
                companies_matched=0,
                candidates_deferred=0,
                candidates_rejected=0,
                candidates_failed=0,
                metadata_json={"provider": HIMALAYAS_PROVIDER, "queries": plan.queries},
            )
        )
        run = self.run_repository.mark_running(run)
        logger.info("Himalayas discovery requested", extra={"run_id": run.id, "query_count": len(plan.passes)})

        query_results: list[HimalayasQueryResult] = []
        accepted_jobs: list[HimalayasAcceptedJobSummary] = []
        rejected_samples: list[HimalayasRejectedCandidateSummary] = []
        seen: dict[str, HimalayasJobPayload] = {}
        provider_records_seen = 0
        malformed_provider_records = 0
        provider_requests_attempted = 0
        provider_pages_completed = 0
        queries_completed = 0
        queries_failed = 0
        query_errors: list[str] = []
        rate_limited = False

        for query_pass in plan.passes:
            if rate_limited or len(seen) >= self.settings.HIMALAYAS_MAX_JOBS_PER_RUN:
                break
            result = HimalayasQueryResult(
                query=query_pass.query,
                query_type=query_pass.query_type,
                country=query_pass.country,
                worldwide=query_pass.worldwide,
            )
            query_failed = False
            previous_page_keys: set[str] | None = None
            for page in range(1, page_limit + 1):
                result.pages_requested += 1
                provider_requests_attempted += 1
                logger.info("Himalayas provider query started", extra={"query": query_pass.query, "query_type": query_pass.query_type, "page": page})
                response = await self._search(query_pass, page)
                if response.reason:
                    result.error = response.reason
                    query_failed = True
                    query_errors.append(response.reason)
                    if response.reason == "himalayas_rate_limited":
                        rate_limited = True
                        logger.info("Himalayas provider rate limited", extra={"run_id": run.id})
                    break
                provider_pages_completed += 1
                malformed_provider_records += response.malformed_records
                records_received = len(response.jobs) + response.malformed_records
                provider_records_seen += records_received
                result.jobs_received += records_received
                page_keys: set[str] = set()
                for job in response.jobs:
                    key = _dedupe_key(job)
                    if key:
                        page_keys.add(key)
                    if not key or key in seen:
                        logger.info("Himalayas provider job deduplicated", extra={"run_id": run.id})
                        continue
                    seen[key] = job
                    result.jobs_unique += 1
                    if len(seen) >= self.settings.HIMALAYAS_MAX_JOBS_PER_RUN:
                        break
                if len(response.jobs) == 0:
                    break
                if previous_page_keys is not None and page_keys and page_keys == previous_page_keys:
                    break
                previous_page_keys = page_keys
                if response.limit and page * response.limit >= response.total_count:
                    break
                if self.settings.HIMALAYAS_REQUEST_DELAY_MS:
                    await asyncio.sleep(self.settings.HIMALAYAS_REQUEST_DELAY_MS / 1000)
            if query_failed:
                queries_failed += 1
            else:
                queries_completed += 1
            query_results.append(result)

        counters = {
            "candidates_created": 0,
            "candidates_existing": 0,
            "candidates_rejected": 0,
            "companies_created": 0,
            "companies_existing": 0,
            "jobs_created": 0,
            "jobs_existing": 0,
            "jobs_updated": 0,
            "jobs_scored": 0,
            "jobs_failed": 0,
        }

        for payload in seen.values():
            try:
                parsed = self.parser.parse(payload)
                candidate, candidate_action = self._candidate_for(run.id, parsed)
                counters["candidates_created" if candidate_action == "created" else "candidates_existing"] += 1
                self._persist_evidence(candidate.id, parsed)
                if not parsed.accepted:
                    counters["candidates_rejected"] += 1
                    self._reject(candidate, parsed.rejection_reason or "rejected")
                    _append_rejected_sample(rejected_samples, parsed)
                    continue
                company, company_action = self._company_for(parsed)
                counters["companies_created" if company_action == "created" else "companies_existing"] += 1
                job, job_action = self._job_for(company, candidate, parsed)
                counters[job_action] += 1
                self.link_repository.ensure_link(job.id, candidate.id)
                self.candidate_repository.update_candidate(
                    candidate,
                    {
                        "status": DiscoveryCandidateStatus.INGESTED,
                        "decision": DiscoveryDecision.CREATED_COMPANY if company_action == "created" else DiscoveryDecision.MATCHED_EXISTING_COMPANY,
                        "matched_company_id": company.id,
                    },
                )
                summary = self._accepted_summary(job, company.name, parsed, _job_action_label(job_action))
                if should_score and job_action in {"jobs_created", "jobs_updated"}:
                    try:
                        match, _ = JobMatchingService(self.session).score_job(profile.id, job.id)
                        counters["jobs_scored"] += 1
                        summary.eligibility_status = match.eligibility_status
                        summary.match_tier = match.match_tier
                        summary.total_score = match.total_score
                    except Exception as exc:
                        self.session.rollback()
                        counters["jobs_failed"] += 1
                        logger.info("Himalayas job scoring failed", extra={"job_id": job.id, "error": exc.__class__.__name__})
                accepted_jobs.append(summary)
            except Exception as exc:
                self.session.rollback()
                counters["jobs_failed"] += 1
                logger.info("Himalayas provider record failed", extra={"run_id": run.id, "error": exc.__class__.__name__})

        for item in query_results:
            item.jobs_accepted = len(accepted_jobs)
            item.jobs_rejected = counters["candidates_rejected"]

        status = self._finish_run(run, queries_completed, queries_failed, counters, provider_records_seen, len(seen), malformed_provider_records)
        finished = datetime.now(timezone.utc)
        accepted_jobs.sort(key=lambda item: (REMOTE_ORDER.get(item.remote_eligibility, 9), TIER_ORDER.get(item.match_tier or "", 9), -(item.total_score or 0)))
        logger.info("Himalayas discovery completed", extra={"run_id": run.id, "status": status, **counters})
        reason = _result_reason(status, rate_limited, query_errors)
        warnings = [*plan.warnings]
        if status == "partial" and query_errors:
            warnings.append(_error_summary(query_errors))
        return HimalayasDiscoveryResult(
            discovery_run_id=run.id,
            status=status,
            reason=reason,
            profile_id=profile.id,
            queries_planned=len(plan.passes),
            queries_completed=queries_completed,
            queries_failed=queries_failed,
            provider_requests_attempted=provider_requests_attempted,
            provider_pages_completed=provider_pages_completed,
            provider_records_seen=provider_records_seen,
            malformed_provider_records=malformed_provider_records,
            unique_records=len(seen),
            accepted_jobs=accepted_jobs[:100],
            rejected_samples=rejected_samples[:20],
            query_results=query_results,
            warnings=warnings,
            started_at=started,
            finished_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
            **counters,
        )

    async def _search(self, query_pass: HimalayasQueryPass, page: int):
        return await self.client.search_jobs(
            query=query_pass.query,
            country=query_pass.country,
            worldwide=query_pass.worldwide,
            exclude_worldwide=query_pass.exclude_worldwide,
            sort=query_pass.sort,
            page=page,
        )

    def _current_profile(self):
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        profile = self.profile_repository.get_by_user_profile_id(user_profile.id)
        if profile is None:
            raise NotFoundError("Job matching profile not found")
        return profile

    def _cooldown_result(self, profile_id: str, now: datetime) -> HimalayasDiscoveryResult | None:
        if self.settings.HIMALAYAS_DISCOVERY_COOLDOWN_HOURS <= 0:
            return None
        latest = self.run_repository.list_runs(source=DiscoverySource.HIMALAYAS, limit=10)
        for run in latest:
            if run.status not in {DiscoveryRunStatus.SUCCESS, DiscoveryRunStatus.PARTIAL_SUCCESS} or not run.finished_at:
                continue
            finished_at = run.finished_at
            if finished_at.tzinfo is None:
                finished_at = finished_at.replace(tzinfo=timezone.utc)
            next_time = finished_at + timedelta(hours=self.settings.HIMALAYAS_DISCOVERY_COOLDOWN_HOURS)
            if next_time > now:
                logger.info("Himalayas discovery cooldown active", extra={"previous_run_id": run.id})
                return HimalayasDiscoveryResult(
                    discovery_run_id=None,
                    status="skipped",
                    reason="himalayas_discovery_cooldown_active",
                    profile_id=profile_id,
                    previous_run_id=run.id,
                    next_eligible_at=next_time,
                    started_at=now,
                    finished_at=now,
                    duration_ms=0,
                )
        return None

    def _candidate_for(self, run_id: str, parsed: ParsedHimalayasJob) -> tuple[DiscoveryCandidate, str]:
        existing = self.candidate_repository.get_by_source_identifier(run_id, DiscoverySource.HIMALAYAS, parsed.source_item_id)
        if existing is not None:
            return existing, "existing"
        candidate = self.candidate_repository.create_candidate(
            DiscoveryCandidate(
                discovery_run_id=run_id,
                source=DiscoverySource.HIMALAYAS,
                source_identifier=parsed.source_item_id,
                raw_name=parsed.company_name,
                raw_website_url=None,
                raw_description=parsed.excerpt,
                raw_country=None,
                normalized_name=_company_key(parsed.company_name),
                normalized_description=parsed.excerpt,
                status=DiscoveryCandidateStatus.NORMALIZED,
                raw_payload=parsed.metadata,
            )
        )
        return candidate, "created"

    def _persist_evidence(self, candidate_id: str, parsed: ParsedHimalayasJob) -> None:
        items = [
            DiscoveryEvidence(
                discovery_candidate_id=candidate_id,
                evidence_type="himalayas_provider_source",
                source_url=parsed.source_url or HIMALAYAS_HOME_URL,
                title=parsed.title,
                excerpt=parsed.excerpt,
                published_at=parsed.published_at,
                metadata_json={
                    "source_name": HIMALAYAS_ATTRIBUTION_LABEL,
                    "attribution_required": True,
                    "attribution_label": HIMALAYAS_ATTRIBUTION_LABEL,
                    "attribution_home_url": HIMALAYAS_HOME_URL,
                },
            ),
            DiscoveryEvidence(
                discovery_candidate_id=candidate_id,
                evidence_type="himalayas_decision",
                source_url=parsed.source_url or HIMALAYAS_HOME_URL,
                title=parsed.title,
                excerpt=parsed.rejection_reason,
                published_at=parsed.published_at,
                metadata_json={**parsed.evidence, "remote_eligibility": parsed.remote_eligibility},
            ),
        ]
        self.evidence_repository.create_many(items)

    def _reject(self, candidate: DiscoveryCandidate, reason: str) -> None:
        self.candidate_repository.update_candidate(
            candidate,
            {
                "status": DiscoveryCandidateStatus.REJECTED,
                "decision": DiscoveryDecision.REJECTED,
                "rejection_reason": reason,
            },
        )

    def _company_for(self, parsed: ParsedHimalayasJob) -> tuple[Company, str]:
        key = _company_key(parsed.company_name)
        existing = self.session.scalar(select(Company).where(func.lower(Company.name) == parsed.company_name.lower()))
        if existing is not None:
            logger.info("Existing company reused", extra={"provider": HIMALAYAS_PROVIDER})
            return existing, "existing"
        source_domain = _source_company_identity(parsed.company_slug or key)
        existing_domain = self.company_repository.get_by_domain(source_domain)
        if existing_domain is not None:
            return existing_domain, "existing"
        company = self.company_repository.create_company(
            Company(
                name=parsed.company_name,
                website_url=None,
                normalized_domain=source_domain,
                description=None,
                country=None,
                stage=CompanyStage.UNKNOWN,
                source=CompanySource.OTHER,
                is_active=True,
            )
        )
        logger.info("Company created", extra={"provider": HIMALAYAS_PROVIDER})
        return company, "created"

    def _job_for(self, company: Company, candidate: DiscoveryCandidate, parsed: ParsedHimalayasJob) -> tuple[Job, str]:
        now = datetime.now(timezone.utc)
        existing = self._existing_job(company.id, parsed)
        if existing is not None:
            values = {"last_seen_at": now, "last_verified_at": now}
            if not existing.apply_url and parsed.source_url:
                values["apply_url"] = parsed.source_url
            if not existing.discovery_candidate_id:
                values["discovery_candidate_id"] = candidate.id
            self.job_repository.update_job(existing, values)
            return existing, "jobs_existing"
        job = self.job_repository.create_job(
            Job(
                company_id=company.id,
                discovery_candidate_id=candidate.id,
                title=parsed.title,
                normalized_title=parsed.normalized_title,
                role_category=parsed.role_category,
                description=parsed.description,
                location=_location_text(parsed),
                remote_type=parsed.remote_type,
                experience_min=parsed.experience_min,
                experience_max=parsed.experience_max,
                salary_min=parsed.salary_min,
                salary_max=parsed.salary_max,
                salary_currency=parsed.salary_currency,
                salary_text=parsed.salary_text,
                seniority=parsed.seniority,
                employment_type=parsed.employment_type,
                job_url=parsed.source_url,
                apply_url=parsed.source_url,
                source_platform=HIMALAYAS_PROVIDER,
                status=JobStatus.ACTIVE,
                first_seen_at=now,
                last_seen_at=now,
                last_verified_at=now,
                published_at=parsed.published_at,
                enrichment_status=JobEnrichmentStatus.ENRICHED.value if parsed.description and parsed.employment_type else JobEnrichmentStatus.PARTIALLY_ENRICHED.value,
                enrichment_confidence=0.86,
                enriched_at=now,
            )
        )
        logger.info("Job created", extra={"provider": HIMALAYAS_PROVIDER, "job_id": job.id})
        return job, "jobs_created"

    def _existing_job(self, company_id: str, parsed: ParsedHimalayasJob) -> Job | None:
        if parsed.source_url:
            existing = self.session.scalar(select(Job).where(Job.job_url == parsed.source_url))
            if existing is not None:
                return existing
            normalized = normalize_job_url(parsed.source_url)
            if normalized.valid:
                existing = self.session.scalar(select(Job).where(Job.job_url == normalized.canonical_url))
                if existing is not None:
                    return existing
        return self.job_repository.get_legacy_match(company_id, parsed.source_url or "", parsed.normalized_title)

    def _accepted_summary(self, job: Job, company_name: str, parsed: ParsedHimalayasJob, action: str) -> HimalayasAcceptedJobSummary:
        return HimalayasAcceptedJobSummary(
            job_id=job.id,
            company_name=company_name,
            title=job.title,
            remote_eligibility=parsed.remote_eligibility,
            seniority=job.seniority,
            employment_type=job.employment_type,
            salary_text=job.salary_text,
            job_url=job.job_url,
            action=action,
        )

    def _finish_run(
        self,
        run: DiscoveryRun,
        queries_completed: int,
        queries_failed: int,
        counters: dict[str, int],
        provider_records_seen: int,
        unique_records: int,
        malformed_provider_records: int,
    ) -> str:
        db_counters = {
            "candidates_found": unique_records,
            "candidates_normalized": counters["candidates_created"] + counters["candidates_existing"],
            "companies_created": counters["companies_created"],
            "companies_matched": counters["companies_existing"],
            "candidates_rejected": counters["candidates_rejected"],
            "candidates_failed": counters["jobs_failed"],
            "metadata_json": {
                "provider": HIMALAYAS_PROVIDER,
                "source": HIMALAYAS_REMOTE_JOBS_SOURCE,
                "provider_records_seen": provider_records_seen,
                "unique_records": unique_records,
                "malformed_provider_records": malformed_provider_records,
            },
        }
        if queries_completed == 0 and queries_failed > 0:
            self.run_repository.mark_failed(run, "himalayas_all_queries_failed", db_counters)
            return "failed"
        if queries_failed > 0:
            self.run_repository.mark_partial_success(run, db_counters)
            return "partial"
        self.run_repository.mark_success(run, db_counters)
        return "succeeded"


def _dedupe_key(payload: HimalayasJobPayload) -> str | None:
    if payload.guid:
        return f"guid:{payload.guid}"
    normalized = normalize_job_url(payload.application_link)
    if normalized.valid:
        return f"url:{normalized.canonical_url}"
    title = re.sub(r"[^a-z0-9]+", " ", str(payload.title or "").lower()).strip()
    if payload.company_slug and title:
        return f"company-title:{payload.company_slug}:{title}"
    return None


def _company_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "unknown"


def _source_company_identity(value: str) -> str:
    return f"himalayas:{_company_key(value)}"


def _location_text(parsed: ParsedHimalayasJob) -> str | None:
    restrictions = parsed.metadata.get("locationRestrictions")
    if not restrictions:
        return "Remote worldwide" if parsed.remote_eligibility == "work_from_anywhere" else "Remote"
    names = [item.get("name") for item in restrictions if isinstance(item, dict) and item.get("name")]
    return ", ".join(names) if names else "Remote"


def _append_rejected_sample(samples: list[HimalayasRejectedCandidateSummary], parsed: ParsedHimalayasJob) -> None:
    if len(samples) >= 20:
        return
    samples.append(
        HimalayasRejectedCandidateSummary(
            source_item_id=parsed.source_item_id,
            title=parsed.title,
            company_name=parsed.company_name,
            rejection_reason=parsed.rejection_reason or "rejected",
            remote_eligibility=parsed.remote_eligibility,
            seniority=parsed.seniority,
        )
    )


def _job_action_label(value: str) -> str:
    return {
        "jobs_created": "created",
        "jobs_existing": "already_exists",
        "jobs_updated": "updated",
    }.get(value, value)


def _result_reason(status: str, rate_limited: bool, errors: list[str]) -> str | None:
    if rate_limited:
        return "himalayas_discovery_rate_limited"
    if status == "failed" and errors:
        unique = sorted(set(errors))
        if len(unique) == 1:
            return f"all_himalayas_queries_failed:{unique[0]}"
        return "all_himalayas_queries_failed:mixed_provider_errors"
    return None


def _error_summary(errors: list[str]) -> str:
    counts = {error: errors.count(error) for error in sorted(set(errors))}
    return "himalayas_query_errors:" + ",".join(f"{key}={value}" for key, value in counts.items())
