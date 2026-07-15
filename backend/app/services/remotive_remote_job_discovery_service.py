import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.discovery.sources.remotive.client import RemotiveRemoteJobsClient
from app.discovery.sources.remotive.constants import (
    REMOTIVE_ATTRIBUTION_LABEL,
    REMOTIVE_HOME_URL,
    REMOTIVE_PROVIDER,
    REMOTIVE_SOURCE,
)
from app.discovery.sources.remotive.filter import RemotiveTargetJobFilter
from app.discovery.sources.remotive.models import RemotiveJobPayload
from app.discovery.sources.remotive.parser import ParsedRemotiveJob, RemotiveJobParser
from app.discovery.sources.remotive.query_planner import RemotiveQueryRequest, RemotiveTargetedQueryPlanner
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
from app.schemas.remotive_discovery import (
    RemotiveAcceptedJobSummary,
    RemotiveDiscoveryResult,
    RemotiveQueryResult,
    RemotiveRejectedCandidateSummary,
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

REMOTE_ORDER = {"work_from_anywhere": 0, "remote_india_eligible": 1, "remote_global_unspecified": 2, "remote_eligibility_unclear": 3}
TIER_ORDER = {"best_match": 0, "strong_match": 1, "worth_checking": 2, "stretch": 3, "unsuitable": 4}


class RemotiveRemoteJobDiscoveryService:
    def __init__(self, session: Session, *, client: RemotiveRemoteJobsClient | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.client = client or RemotiveRemoteJobsClient()
        self.query_planner = RemotiveTargetedQueryPlanner()
        self.parser = RemotiveJobParser()
        self.filter = RemotiveTargetJobFilter()
        self.run_repository = DiscoveryRunRepository(session)
        self.candidate_repository = DiscoveryCandidateRepository(session)
        self.evidence_repository = DiscoveryEvidenceRepository(session)
        self.company_repository = CompanyRepository(session)
        self.job_repository = JobRepository(session)
        self.link_repository = JobDiscoveryLinkRepository(session)
        self.user_profile_repository = UserProfileRepository(session)
        self.profile_repository = JobMatchingProfileRepository(session)

    def query_plan_result(self, *, max_requests: int | None = None, limit_per_request: int | None = None) -> dict[str, Any]:
        profile = self._current_profile()
        request_cap = min(max_requests or self.settings.REMOTIVE_MAX_REQUESTS_PER_RUN, self.settings.REMOTIVE_MAX_REQUESTS_PER_RUN)
        limit = min(limit_per_request or self.settings.REMOTIVE_MAX_JOBS_PER_REQUEST, self.settings.REMOTIVE_MAX_JOBS_PER_REQUEST)
        plan = self.query_planner.build_plan(
            profile,
            max_requests=request_cap,
            limit=limit,
            software_category_enabled=self.settings.REMOTIVE_SOFTWARE_CATEGORY_ENABLED,
        )
        cooldown = self._cooldown(datetime.now(timezone.utc))
        return {
            "profile_target_roles": list(profile.target_titles_json or []),
            "planned_requests": [vars(item) for item in plan.requests],
            "total_planned_requests": len(plan.requests),
            "configured_request_cap": self.settings.REMOTIVE_MAX_REQUESTS_PER_RUN,
            "generated_from_profile": plan.generated_from_profile,
            "canonical_target_roles": plan.canonical_target_roles,
            "cooldown_active": cooldown is not None,
            "previous_run_id": cooldown[0].id if cooldown else None,
            "next_eligible_at": cooldown[1] if cooldown else None,
            "warnings": plan.warnings,
        }

    async def run_discovery(
        self,
        *,
        force: bool = False,
        max_requests: int | None = None,
        limit_per_request: int | None = None,
        score_after_ingestion: bool | None = None,
    ) -> RemotiveDiscoveryResult:
        started = datetime.now(timezone.utc)
        if not self.settings.REMOTIVE_DISCOVERY_ENABLED:
            raise AppError("REMOTIVE_DISCOVERY_DISABLED", "Remotive discovery is disabled", status_code=503)
        profile = self._current_profile()
        cooldown = None if force else self._cooldown(started)
        if cooldown:
            run, next_time = cooldown
            return RemotiveDiscoveryResult(
                status="skipped",
                reason="remotive_discovery_cooldown_active",
                profile_id=profile.id,
                previous_run_id=run.id,
                next_eligible_at=next_time,
                started_at=started,
                finished_at=started,
                duration_ms=0,
            )

        request_cap = min(max_requests or self.settings.REMOTIVE_MAX_REQUESTS_PER_RUN, self.settings.REMOTIVE_MAX_REQUESTS_PER_RUN)
        limit = min(limit_per_request or self.settings.REMOTIVE_MAX_JOBS_PER_REQUEST, self.settings.REMOTIVE_MAX_JOBS_PER_REQUEST)
        should_score = self.settings.REMOTIVE_SCORE_AFTER_INGESTION if score_after_ingestion is None else score_after_ingestion
        plan = self.query_planner.build_plan(
            profile,
            max_requests=request_cap,
            limit=limit,
            software_category_enabled=self.settings.REMOTIVE_SOFTWARE_CATEGORY_ENABLED,
        )
        run = self.run_repository.create_run(
            DiscoveryRun(
                source=DiscoverySource.REMOTIVE,
                status=DiscoveryRunStatus.PENDING,
                candidates_found=0,
                candidates_normalized=0,
                companies_created=0,
                companies_matched=0,
                candidates_deferred=0,
                candidates_rejected=0,
                candidates_failed=0,
                metadata_json={"provider": REMOTIVE_PROVIDER, "source": REMOTIVE_SOURCE},
            )
        )
        run = self.run_repository.mark_running(run)
        logger.info("Remotive discovery requested", extra={"run_id": run.id, "request_count": len(plan.requests)})

        query_results: list[RemotiveQueryResult] = []
        seen: dict[str, tuple[RemotiveJobPayload, RemotiveQueryResult]] = {}
        provider_records_seen = malformed_records = duplicate_records = requests_completed = requests_failed = 0
        query_errors: list[str] = []
        rate_limited = False

        for request in plan.requests:
            if rate_limited or len(seen) >= self.settings.REMOTIVE_MAX_JOBS_PER_RUN:
                break
            result = RemotiveQueryResult(request_type=request.request_type, category=request.category, search_term=request.search_term)
            logger.info("Remotive provider request started", extra={"request_type": request.request_type, "category": request.category, "search": request.search_term})
            response = await self._list_jobs(request)
            result.http_status = response.status_code
            result.malformed_records = len(response.malformed_jobs)
            malformed_records += len(response.malformed_jobs)
            if response.reason:
                result.error = response.reason
                query_errors.append(response.reason)
                requests_failed += 1
                if response.reason == "remotive_rate_limited":
                    rate_limited = True
                query_results.append(result)
                continue
            requests_completed += 1
            received = len(response.jobs) + len(response.malformed_jobs)
            provider_records_seen += received
            result.jobs_received = received
            for job in response.jobs:
                key = _dedupe_key(job)
                if not key or key in seen:
                    duplicate_records += 1
                    logger.info("Remotive provider job deduplicated", extra={"run_id": run.id})
                    continue
                seen[key] = (job, result)
                result.unique_jobs += 1
                if len(seen) >= self.settings.REMOTIVE_MAX_JOBS_PER_RUN:
                    break
            query_results.append(result)
            if self.settings.REMOTIVE_REQUEST_DELAY_MS and request is not plan.requests[-1]:
                await asyncio.sleep(self.settings.REMOTIVE_REQUEST_DELAY_MS / 1000)

        counters = {key: 0 for key in ("candidates_created", "candidates_existing", "candidates_rejected", "companies_created", "companies_existing", "jobs_created", "jobs_existing", "jobs_updated", "jobs_scored", "jobs_failed")}
        accepted_jobs: list[RemotiveAcceptedJobSummary] = []
        rejected_samples: list[RemotiveRejectedCandidateSummary] = []

        for payload, query_result in seen.values():
            try:
                parsed = self.filter.evaluate(self.parser.parse(payload), max_age_days=self.settings.REMOTIVE_MAX_JOB_AGE_DAYS)
                candidate, action = self._candidate_for(run.id, parsed)
                counters["candidates_created" if action == "created" else "candidates_existing"] += 1
                self._persist_evidence(candidate.id, parsed)
                if not parsed.accepted:
                    counters["candidates_rejected"] += 1
                    query_result.jobs_rejected += 1
                    self._reject(candidate, parsed.rejection_reason or "rejected")
                    _append_rejected(rejected_samples, parsed)
                    continue
                company, company_action = self._company_for(parsed)
                counters["companies_created" if company_action == "created" else "companies_existing"] += 1
                job, job_action = self._job_for(company, candidate, parsed)
                counters[job_action] += 1
                query_result.jobs_accepted += 1
                self.link_repository.ensure_link(job.id, candidate.id)
                self.candidate_repository.update_candidate(candidate, {"status": DiscoveryCandidateStatus.INGESTED, "decision": DiscoveryDecision.CREATED_COMPANY if company_action == "created" else DiscoveryDecision.MATCHED_EXISTING_COMPANY, "matched_company_id": company.id})
                summary = self._summary(job, company.name, parsed, _job_action_label(job_action))
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
                        logger.info("Remotive job scoring failed", extra={"job_id": job.id, "error": exc.__class__.__name__})
                if summary.eligibility_status != "unsuitable":
                    accepted_jobs.append(summary)
            except Exception as exc:
                self.session.rollback()
                counters["jobs_failed"] += 1
                logger.info("Remotive provider record failed", extra={"run_id": run.id, "error": exc.__class__.__name__})

        status, reason = self._finish(run, requests_completed, requests_failed, counters, provider_records_seen, len(seen), duplicate_records, malformed_records, query_errors, rate_limited)
        finished = datetime.now(timezone.utc)
        accepted_jobs.sort(key=lambda item: (REMOTE_ORDER.get(item.remote_eligibility, 9), TIER_ORDER.get(item.match_tier or "", 9), -(item.total_score or 0), -(item.published_at or datetime(1970, 1, 1, tzinfo=timezone.utc)).timestamp()))
        warnings = [*plan.warnings]
        if query_errors:
            warnings.append(_error_summary(query_errors))
        return RemotiveDiscoveryResult(
            discovery_run_id=run.id,
            status=status,
            reason=reason,
            profile_id=profile.id,
            requests_planned=len(plan.requests),
            requests_completed=requests_completed,
            requests_failed=requests_failed,
            provider_records_seen=provider_records_seen,
            unique_records=len(seen),
            duplicate_records=duplicate_records,
            malformed_records=malformed_records,
            accepted_jobs=accepted_jobs[:100],
            rejected_samples=rejected_samples[:20],
            query_results=query_results,
            warnings=warnings,
            started_at=started,
            finished_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
            **counters,
        )

    async def _list_jobs(self, request: RemotiveQueryRequest):
        return await self.client.list_jobs(category=request.category, search=request.search_term, limit=request.limit)

    def _current_profile(self):
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        profile = self.profile_repository.get_by_user_profile_id(user_profile.id)
        if profile is None:
            raise NotFoundError("Job matching profile not found")
        return profile

    def _cooldown(self, now: datetime):
        if self.settings.REMOTIVE_DISCOVERY_COOLDOWN_HOURS <= 0:
            return None
        for run in self.run_repository.list_runs(source=DiscoverySource.REMOTIVE, limit=10):
            if run.status not in {DiscoveryRunStatus.SUCCESS, DiscoveryRunStatus.PARTIAL_SUCCESS} or not run.finished_at:
                continue
            finished = run.finished_at if run.finished_at.tzinfo else run.finished_at.replace(tzinfo=timezone.utc)
            next_time = finished + timedelta(hours=self.settings.REMOTIVE_DISCOVERY_COOLDOWN_HOURS)
            if next_time > now:
                return run, next_time
        return None

    def _candidate_for(self, run_id: str, parsed: ParsedRemotiveJob):
        existing = self.candidate_repository.get_by_source_identifier(run_id, DiscoverySource.REMOTIVE, parsed.source_item_id)
        if existing:
            return existing, "existing"
        candidate = self.candidate_repository.create_candidate(
            DiscoveryCandidate(
                discovery_run_id=run_id,
                source=DiscoverySource.REMOTIVE,
                source_identifier=parsed.source_item_id,
                raw_name=parsed.company_name or parsed.title or "Remotive job",
                raw_website_url=None,
                raw_description=parsed.excerpt,
                raw_country=None,
                normalized_name=_company_key(parsed.company_name),
                normalized_description=parsed.excerpt,
                status=DiscoveryCandidateStatus.NORMALIZED,
                raw_payload={**parsed.metadata, "role_match_type": parsed.role_match_type, "remote_eligibility": parsed.remote_eligibility},
            )
        )
        return candidate, "created"

    def _persist_evidence(self, candidate_id: str, parsed: ParsedRemotiveJob) -> None:
        self.evidence_repository.create_many([
            DiscoveryEvidence(
                discovery_candidate_id=candidate_id,
                evidence_type="remotive_provider_source",
                source_url=parsed.source_url or REMOTIVE_HOME_URL,
                title=parsed.title,
                excerpt=parsed.excerpt,
                published_at=parsed.published_at,
                metadata_json={"attribution_required": True, "attribution_label": REMOTIVE_ATTRIBUTION_LABEL, "attribution_home_url": REMOTIVE_HOME_URL, "attribution_job_url": parsed.source_url, "source_item_id": parsed.source_item_id, "category": parsed.category},
            ),
            DiscoveryEvidence(
                discovery_candidate_id=candidate_id,
                evidence_type="remotive_decision",
                source_url=parsed.source_url or REMOTIVE_HOME_URL,
                title=parsed.title,
                excerpt=parsed.rejection_reason,
                published_at=parsed.published_at,
                metadata_json={**parsed.evidence, "remote_eligibility": parsed.remote_eligibility, "job_type": parsed.employment_type, "salary_text": parsed.salary_text},
            ),
        ])

    def _reject(self, candidate: DiscoveryCandidate, reason: str) -> None:
        self.candidate_repository.update_candidate(candidate, {"status": DiscoveryCandidateStatus.REJECTED, "decision": DiscoveryDecision.REJECTED, "rejection_reason": reason})

    def _company_for(self, parsed: ParsedRemotiveJob):
        name = parsed.company_name or ""
        existing = self.session.scalar(select(Company).where(func.lower(Company.name) == name.lower()))
        if existing:
            return existing, "existing"
        source_identity = f"remotive:{_company_key(name)}"
        existing = self.company_repository.get_by_domain(source_identity)
        if existing:
            return existing, "existing"
        return self.company_repository.create_company(Company(name=name, website_url=None, normalized_domain=source_identity, description=None, country=None, stage=CompanyStage.UNKNOWN, source=CompanySource.OTHER, is_active=True)), "created"

    def _job_for(self, company: Company, candidate: DiscoveryCandidate, parsed: ParsedRemotiveJob):
        now = datetime.now(timezone.utc)
        existing = self._existing_job(company.id, parsed)
        if existing:
            updates = {"last_seen_at": now, "last_verified_at": now}
            if not existing.discovery_candidate_id:
                updates["discovery_candidate_id"] = candidate.id
            if not existing.apply_url and parsed.source_url:
                updates["apply_url"] = parsed.source_url
            self.job_repository.update_job(existing, updates)
            return existing, "jobs_existing"
        job = self.job_repository.create_job(
            Job(
                company_id=company.id,
                discovery_candidate_id=candidate.id,
                title=parsed.title,
                normalized_title=parsed.normalized_title,
                role_category=parsed.role_category,
                description=parsed.description,
                location=parsed.location or "Remote",
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
                published_at=parsed.published_at,
                first_seen_at=now,
                last_seen_at=now,
                last_verified_at=now,
                source_platform=REMOTIVE_SOURCE,
                status=JobStatus.ACTIVE,
                enrichment_status=JobEnrichmentStatus.ENRICHED.value if parsed.description and parsed.location else JobEnrichmentStatus.PARTIALLY_ENRICHED.value,
                enrichment_confidence=0.82,
                enriched_at=now,
            )
        )
        return job, "jobs_created"

    def _existing_job(self, company_id: str, parsed: ParsedRemotiveJob) -> Job | None:
        if parsed.source_url:
            existing = self.session.scalar(select(Job).where(Job.job_url == parsed.source_url))
            if existing:
                return existing
        return self.job_repository.get_legacy_match(company_id, parsed.source_url or "", parsed.normalized_title)

    def _summary(self, job: Job, company_name: str, parsed: ParsedRemotiveJob, action: str) -> RemotiveAcceptedJobSummary:
        return RemotiveAcceptedJobSummary(
            job_id=job.id,
            company_name=company_name,
            title=job.title,
            remote_eligibility=parsed.remote_eligibility or "remote_eligibility_unclear",
            seniority=job.seniority,
            employment_type=job.employment_type,
            salary_text=job.salary_text,
            published_at=job.published_at,
            job_url=job.job_url,
            action=action,
            attribution_label=REMOTIVE_ATTRIBUTION_LABEL,
        )

    def _finish(self, run: DiscoveryRun, completed: int, failed: int, counters: dict[str, int], seen: int, unique: int, duplicates: int, malformed: int, errors: list[str], rate_limited: bool):
        db_counters = {"candidates_found": unique, "candidates_normalized": counters["candidates_created"] + counters["candidates_existing"], "companies_created": counters["companies_created"], "companies_matched": counters["companies_existing"], "candidates_rejected": counters["candidates_rejected"], "candidates_failed": counters["jobs_failed"], "metadata_json": {"provider": REMOTIVE_PROVIDER, "provider_records_seen": seen, "unique_records": unique, "duplicate_records": duplicates, "malformed_records": malformed}}
        if completed == 0 and failed > 0:
            reason = "remotive_all_queries_failed"
            self.run_repository.mark_failed(run, reason, db_counters)
            return "failed", _result_reason("failed", rate_limited, errors) or reason
        if failed > 0:
            self.run_repository.mark_partial_success(run, db_counters)
            return "partial", _result_reason("partial", rate_limited, errors) or "remotive_partial_query_failure"
        self.run_repository.mark_success(run, db_counters)
        return "succeeded", _result_reason("succeeded", rate_limited, errors)


def _dedupe_key(payload: RemotiveJobPayload) -> str | None:
    if payload.source_id:
        return f"id:{payload.source_id}"
    if payload.url:
        return f"url:{payload.url}"
    if payload.company_name and payload.title:
        pub = payload.publication_date.isoformat() if payload.publication_date else ""
        return f"title:{_company_key(payload.company_name)}:{_company_key(payload.title)}:{pub}"
    return None


def _company_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "unknown").lower()).strip("-") or "unknown"


def _append_rejected(samples: list[RemotiveRejectedCandidateSummary], parsed: ParsedRemotiveJob) -> None:
    if len(samples) >= 20:
        return
    samples.append(RemotiveRejectedCandidateSummary(source_item_id=parsed.source_item_id, company_name=parsed.company_name, title=parsed.title, rejection_reason=parsed.rejection_reason or "rejected", remote_eligibility=parsed.remote_eligibility, seniority=parsed.seniority))


def _job_action_label(value: str) -> str:
    return {"jobs_created": "created", "jobs_existing": "already_exists", "jobs_updated": "updated"}.get(value, value)


def _result_reason(status: str, rate_limited: bool, errors: list[str]) -> str | None:
    if rate_limited:
        return "remotive_discovery_rate_limited"
    if status == "failed" and errors:
        unique = sorted(set(errors))
        return f"all_remotive_queries_failed:{unique[0]}" if len(unique) == 1 else "all_remotive_queries_failed:mixed_provider_errors"
    if status == "partial" and errors:
        return "remotive_partial_query_failure"
    return None


def _error_summary(errors: list[str]) -> str:
    counts = {error: errors.count(error) for error in sorted(set(errors))}
    return "remotive_query_errors:" + ",".join(f"{key}={value}" for key, value in counts.items())
