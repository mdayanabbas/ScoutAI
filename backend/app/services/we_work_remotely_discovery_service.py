import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.discovery.sources.we_work_remotely.client import WeWorkRemotelyRSSClient
from app.discovery.sources.we_work_remotely.constants import WWR_ATTRIBUTION_LABEL, WWR_HOME_URL, WWR_PROVIDER, WWR_RSS_SOURCE
from app.discovery.sources.we_work_remotely.filter import WWRFilterResult, WWRTargetJobFilter
from app.discovery.sources.we_work_remotely.models import WWRFeedDefinition, WWRFeedItem
from app.discovery.sources.we_work_remotely.normalizer import normalized_identity
from app.discovery.sources.we_work_remotely.parser import WeWorkRemotelyRSSParser
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
from app.schemas.we_work_remotely_discovery import (
    WWRAcceptedJobSummary,
    WWRDiscoveryResult,
    WWRFeedResult,
    WWRRejectedCandidateSummary,
)
from app.services.job_matching_service import JobMatchingService
from app.utils.enums import CompanySource, CompanyStage, DiscoveryCandidateStatus, DiscoveryDecision, DiscoveryRunStatus, DiscoverySource, JobEnrichmentStatus, JobStatus

logger = logging.getLogger(__name__)

REMOTE_ORDER = {"work_from_anywhere": 0, "remote_india_eligible": 1, "remote_global_unspecified": 2, "remote_eligibility_unclear": 3}
TIER_ORDER = {"best_match": 0, "strong_match": 1, "worth_checking": 2, "stretch": 3, "unsuitable": 4}


class WeWorkRemotelyDiscoveryService:
    def __init__(self, session: Session, *, client: WeWorkRemotelyRSSClient | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.client = client or WeWorkRemotelyRSSClient()
        self.parser = WeWorkRemotelyRSSParser()
        self.filter = WWRTargetJobFilter()
        self.run_repository = DiscoveryRunRepository(session)
        self.candidate_repository = DiscoveryCandidateRepository(session)
        self.evidence_repository = DiscoveryEvidenceRepository(session)
        self.company_repository = CompanyRepository(session)
        self.job_repository = JobRepository(session)
        self.link_repository = JobDiscoveryLinkRepository(session)
        self.user_profile_repository = UserProfileRepository(session)
        self.profile_repository = JobMatchingProfileRepository(session)

    def feed_plan_result(self, *, include_all_other: bool | None = None) -> dict[str, Any]:
        profile = self._current_profile()
        feeds = self._feed_plan(include_all_other=include_all_other)
        cooldown = self._cooldown(datetime.now(timezone.utc))
        return {
            "enabled_feeds": [{"feed_type": f.feed_type, "host_path": _safe_host_path(f.feed_url), "priority": f.priority} for f in feeds],
            "profile_target_roles": list(profile.target_titles_json or []),
            "accepted_employment_types": list(profile.accepted_employment_types_json or []),
            "remote_eligibility_policy": ["work_from_anywhere", "remote_india_eligible", "remote_global_unspecified", "remote_eligibility_unclear"],
            "maximum_items": self.settings.WWR_MAX_ITEMS_PER_FEED,
            "cooldown_active": cooldown is not None,
            "previous_run_id": cooldown[0].id if cooldown else None,
            "next_eligible_at": cooldown[1] if cooldown else None,
            "warnings": [],
        }

    async def run_discovery(
        self,
        *,
        force: bool = False,
        include_all_other: bool | None = None,
        max_items_per_feed: int | None = None,
        score_after_ingestion: bool | None = None,
    ) -> WWRDiscoveryResult:
        started = datetime.now(timezone.utc)
        if not self.settings.WWR_DISCOVERY_ENABLED:
            raise AppError("WWR_DISCOVERY_DISABLED", "We Work Remotely discovery is disabled", status_code=503)
        profile = self._current_profile()
        cooldown = None if force else self._cooldown(started)
        if cooldown:
            run, next_time = cooldown
            return WWRDiscoveryResult(status="skipped", reason="wwr_discovery_cooldown_active", profile_id=profile.id, previous_run_id=run.id, next_eligible_at=next_time, started_at=started, finished_at=started, duration_ms=0)

        feeds = self._feed_plan(include_all_other=include_all_other)
        limit = min(max_items_per_feed or self.settings.WWR_MAX_ITEMS_PER_FEED, self.settings.WWR_MAX_ITEMS_PER_FEED)
        job_limit = self.settings.WWR_MAX_JOBS_PER_RUN
        should_score = self.settings.WWR_SCORE_AFTER_INGESTION if score_after_ingestion is None else score_after_ingestion
        run = self.run_repository.create_run(DiscoveryRun(source=DiscoverySource.WE_WORK_REMOTELY, status=DiscoveryRunStatus.PENDING, candidates_found=0, candidates_normalized=0, companies_created=0, companies_matched=0, candidates_deferred=0, candidates_rejected=0, candidates_failed=0, metadata_json={"provider": WWR_PROVIDER, "source": WWR_RSS_SOURCE}))
        run = self.run_repository.mark_running(run)
        logger.info("WWR discovery requested", extra={"run_id": run.id, "feeds": len(feeds)})

        feed_results: list[WWRFeedResult] = []
        seen: dict[str, tuple[WWRFeedItem, WWRFilterResult]] = {}
        rejected_samples: list[WWRRejectedCandidateSummary] = []
        accepted_jobs: list[WWRAcceptedJobSummary] = []
        counters = {key: 0 for key in ("candidates_created", "candidates_existing", "candidates_rejected", "companies_created", "companies_existing", "jobs_created", "jobs_existing", "jobs_updated", "jobs_scored", "jobs_failed")}
        feeds_completed = feeds_failed = feeds_not_modified = malformed_items = feed_items_seen = 0

        for feed in feeds:
            fr = WWRFeedResult(feed_type=feed.feed_type, status="failed")
            response = await self.client.fetch_feed(feed)
            fr.http_status = response.status_code
            if response.not_modified:
                fr.status = "not_modified"
                fr.not_modified = True
                feeds_completed += 1
                feeds_not_modified += 1
                feed_results.append(fr)
                continue
            if not response.success or not response.body:
                fr.error = response.reason or "wwr_feed_failed"
                feeds_failed += 1
                feed_results.append(fr)
                continue
            parsed = self.parser.parse(response.body, feed=feed)
            if parsed.warnings and not parsed.items:
                fr.error = parsed.warnings[0]
                feeds_failed += 1
                feed_results.append(fr)
                continue
            feeds_completed += 1
            fr.status = "completed"
            fr.items_received = len(parsed.items) + len(parsed.malformed_items)
            fr.valid_items = min(len(parsed.items), limit)
            fr.malformed_items = len(parsed.malformed_items)
            malformed_items += len(parsed.malformed_items)
            feed_items_seen += fr.items_received
            for item in parsed.items[:limit]:
                evaluation = self.filter.evaluate(item, max_age_days=self.settings.WWR_MAX_JOB_AGE_DAYS)
                key = _dedupe_key(item)
                if not key or key in seen:
                    continue
                seen[key] = (item, evaluation)
                fr.unique_items += 1
            feed_results.append(fr)

        for item, evaluation in seen.values():
            try:
                if evaluation.accepted and (counters["jobs_created"] + counters["jobs_existing"] + counters["jobs_updated"]) >= job_limit:
                    continue
                candidate, action = self._candidate_for(run.id, item, evaluation)
                counters["candidates_created" if action == "created" else "candidates_existing"] += 1
                self._persist_evidence(candidate.id, item, evaluation)
                if not evaluation.accepted:
                    counters["candidates_rejected"] += 1
                    self._reject(candidate, evaluation.rejection_reason or "rejected")
                    _append_rejected(rejected_samples, item, evaluation)
                    continue
                company, company_action = self._company_for(item)
                counters["companies_created" if company_action == "created" else "companies_existing"] += 1
                job, job_action = self._job_for(company, candidate, item, evaluation)
                counters[job_action] += 1
                self.link_repository.ensure_link(job.id, candidate.id)
                self.candidate_repository.update_candidate(candidate, {"status": DiscoveryCandidateStatus.INGESTED, "decision": DiscoveryDecision.CREATED_COMPANY if company_action == "created" else DiscoveryDecision.MATCHED_EXISTING_COMPANY, "matched_company_id": company.id})
                summary = self._summary(job, company.name, item, evaluation, _job_action_label(job_action))
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
                        logger.info("WWR job scoring failed", extra={"job_id": job.id, "error": exc.__class__.__name__})
                if summary.eligibility_status != "unsuitable":
                    accepted_jobs.append(summary)
            except Exception as exc:
                self.session.rollback()
                counters["jobs_failed"] += 1
                logger.info("WWR item failed", extra={"run_id": run.id, "error": exc.__class__.__name__})

        for result in feed_results:
            result.accepted_items = len(accepted_jobs)
            result.rejected_items = counters["candidates_rejected"]
        status, reason = self._finish(run, feeds_completed, feeds_failed, counters, len(seen), malformed_items, feed_items_seen)
        finished = datetime.now(timezone.utc)
        accepted_jobs.sort(key=lambda x: (REMOTE_ORDER.get(x.remote_eligibility, 9), TIER_ORDER.get(x.match_tier or "", 9), -(x.total_score or 0), -(x.published_at or datetime(1970, 1, 1, tzinfo=timezone.utc)).timestamp()))
        return WWRDiscoveryResult(discovery_run_id=run.id, status=status, reason=reason, profile_id=profile.id, feeds_planned=len(feeds), feeds_completed=feeds_completed, feeds_failed=feeds_failed, feeds_not_modified=feeds_not_modified, feed_items_seen=feed_items_seen, unique_items=len(seen), malformed_items=malformed_items, accepted_jobs=accepted_jobs[:100], rejected_samples=rejected_samples[:20], feed_results=feed_results, started_at=started, finished_at=finished, duration_ms=int((finished - started).total_seconds() * 1000), **counters)

    def _feed_plan(self, *, include_all_other: bool | None = None) -> list[WWRFeedDefinition]:
        include_other = self.settings.WWR_INCLUDE_ALL_OTHER_FEED if include_all_other is None else include_all_other
        feeds = [WWRFeedDefinition("Programming", "programming", self.settings.WWR_PROGRAMMING_RSS_URL, True, 0)]
        if include_other:
            feeds.append(WWRFeedDefinition("All Other Remote Jobs", "all_other", self.settings.WWR_ALL_OTHER_RSS_URL, True, 1))
        return feeds

    def _current_profile(self):
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        profile = self.profile_repository.get_by_user_profile_id(user_profile.id)
        if profile is None:
            raise NotFoundError("Job matching profile not found")
        return profile

    def _cooldown(self, now: datetime):
        if self.settings.WWR_DISCOVERY_COOLDOWN_HOURS <= 0:
            return None
        for run in self.run_repository.list_runs(source=DiscoverySource.WE_WORK_REMOTELY, limit=10):
            if run.status not in {DiscoveryRunStatus.SUCCESS, DiscoveryRunStatus.PARTIAL_SUCCESS} or not run.finished_at:
                continue
            finished = run.finished_at if run.finished_at.tzinfo else run.finished_at.replace(tzinfo=timezone.utc)
            next_time = finished + timedelta(hours=self.settings.WWR_DISCOVERY_COOLDOWN_HOURS)
            if next_time > now:
                return run, next_time
        return None

    def _candidate_for(self, run_id: str, item: WWRFeedItem, evaluation: WWRFilterResult):
        source_id = _source_id(item)
        existing = self.candidate_repository.get_by_source_identifier(run_id, DiscoverySource.WE_WORK_REMOTELY, source_id)
        if existing:
            return existing, "existing"
        candidate = self.candidate_repository.create_candidate(DiscoveryCandidate(discovery_run_id=run_id, source=DiscoverySource.WE_WORK_REMOTELY, source_identifier=source_id, raw_name=item.company_name or item.title or "WWR job", raw_website_url=None, raw_description=(item.description_text or "")[:500], raw_country=None, normalized_name=normalized_identity(item.company_name), normalized_description=(item.description_text or "")[:500], status=DiscoveryCandidateStatus.NORMALIZED, raw_payload={"source_feed": item.source_feed, "categories": item.categories, "remote_eligibility": evaluation.remote_eligibility, "role_match_type": evaluation.role_match_type, "published_at": item.published_at.isoformat() if item.published_at else None}))
        return candidate, "created"

    def _persist_evidence(self, candidate_id: str, item: WWRFeedItem, evaluation: WWRFilterResult) -> None:
        self.evidence_repository.create_many([
            DiscoveryEvidence(discovery_candidate_id=candidate_id, evidence_type="wwr_source", source_url=item.link or WWR_HOME_URL, title=item.title, excerpt=(item.description_text or "")[:500], published_at=item.published_at, metadata_json={"attribution_required": True, "attribution_label": WWR_ATTRIBUTION_LABEL, "attribution_home_url": WWR_HOME_URL, "attribution_job_url": item.link, "source_feed": item.source_feed}),
            DiscoveryEvidence(discovery_candidate_id=candidate_id, evidence_type="wwr_decision", source_url=item.link or WWR_HOME_URL, title=item.role_title or item.title, excerpt=evaluation.rejection_reason, published_at=item.published_at, metadata_json=evaluation.evidence | {"remote_eligibility": evaluation.remote_eligibility}),
        ])

    def _reject(self, candidate: DiscoveryCandidate, reason: str) -> None:
        self.candidate_repository.update_candidate(candidate, {"status": DiscoveryCandidateStatus.REJECTED, "decision": DiscoveryDecision.REJECTED, "rejection_reason": reason})

    def _company_for(self, item: WWRFeedItem):
        name = item.company_name or ""
        existing = self.session.scalar(select(Company).where(func.lower(Company.name) == name.lower()))
        if existing:
            return existing, "existing"
        source_identity = f"wwr:{normalized_identity(name)}"
        existing = self.company_repository.get_by_domain(source_identity)
        if existing:
            return existing, "existing"
        return self.company_repository.create_company(Company(name=name, website_url=None, normalized_domain=source_identity, description=None, country=None, stage=CompanyStage.UNKNOWN, source=CompanySource.OTHER, is_active=True)), "created"

    def _job_for(self, company: Company, candidate: DiscoveryCandidate, item: WWRFeedItem, evaluation: WWRFilterResult):
        now = datetime.now(timezone.utc)
        existing = self.session.scalar(select(Job).where(Job.job_url == item.link))
        if existing:
            self.job_repository.update_job(existing, {"last_seen_at": now, "last_verified_at": now})
            return existing, "jobs_existing"
        title = item.role_title or item.title or "Remote role"
        job = self.job_repository.create_job(Job(company_id=company.id, discovery_candidate_id=candidate.id, title=title, normalized_title=normalized_identity(title).replace("-", " "), role_category=evaluation.role_category, description=item.description_text, location=item.region_text or "Remote", remote_type=evaluation.remote_type, experience_min=evaluation.experience_min, experience_max=evaluation.experience_max, salary_min=evaluation.salary_min, salary_max=evaluation.salary_max, salary_currency=evaluation.salary_currency, salary_text=evaluation.salary_text, seniority=evaluation.seniority, employment_type=evaluation.employment_type, job_url=item.link, apply_url=item.link, published_at=item.published_at, first_seen_at=now, last_seen_at=now, last_verified_at=now, source_platform=WWR_PROVIDER, status=JobStatus.ACTIVE, enrichment_status=JobEnrichmentStatus.ENRICHED.value if item.description_text else JobEnrichmentStatus.PARTIALLY_ENRICHED.value, enrichment_confidence=0.78, enriched_at=now))
        return job, "jobs_created"

    def _summary(self, job: Job, company_name: str, item: WWRFeedItem, evaluation: WWRFilterResult, action: str) -> WWRAcceptedJobSummary:
        return WWRAcceptedJobSummary(job_id=job.id, company_name=company_name, title=job.title, remote_eligibility=evaluation.remote_eligibility, seniority=job.seniority, employment_type=job.employment_type, salary_text=job.salary_text, published_at=job.published_at, job_url=job.job_url, action=action, attribution_label=WWR_ATTRIBUTION_LABEL)

    def _finish(self, run: DiscoveryRun, completed: int, failed: int, counters: dict[str, int], unique: int, malformed: int, seen: int):
        db_counters = {"candidates_found": unique, "candidates_normalized": counters["candidates_created"] + counters["candidates_existing"], "companies_created": counters["companies_created"], "companies_matched": counters["companies_existing"], "candidates_rejected": counters["candidates_rejected"], "candidates_failed": counters["jobs_failed"], "metadata_json": {"provider": WWR_PROVIDER, "source": WWR_RSS_SOURCE, "feed_items_seen": seen, "unique_items": unique, "malformed_items": malformed}}
        if completed == 0 and failed > 0:
            self.run_repository.mark_failed(run, "wwr_all_feeds_failed", db_counters)
            return "failed", "wwr_all_feeds_failed"
        if failed:
            self.run_repository.mark_partial_success(run, db_counters)
            return "partial", "wwr_partial_feed_failure"
        self.run_repository.mark_success(run, db_counters)
        return "succeeded", None


def _source_id(item: WWRFeedItem) -> str:
    return item.guid or item.link or f"{normalized_identity(item.company_name)}:{normalized_identity(item.role_title or item.title)}:{item.published_at.isoformat() if item.published_at else ''}"


def _dedupe_key(item: WWRFeedItem) -> str | None:
    if item.guid:
        return f"guid:{item.guid}"
    if item.link:
        return f"url:{item.link}"
    if item.company_name and item.role_title:
        return f"title:{normalized_identity(item.company_name)}:{normalized_identity(item.role_title)}:{item.published_at.isoformat() if item.published_at else ''}"
    return None


def _append_rejected(samples: list[WWRRejectedCandidateSummary], item: WWRFeedItem, evaluation: WWRFilterResult) -> None:
    if len(samples) >= 20:
        return
    samples.append(WWRRejectedCandidateSummary(source_item_id=_source_id(item), title=item.role_title or item.title, company_name=item.company_name, rejection_reason=evaluation.rejection_reason or "rejected", remote_eligibility=evaluation.remote_eligibility, seniority=evaluation.seniority))


def _job_action_label(value: str) -> str:
    return {"jobs_created": "created", "jobs_existing": "already_exists", "jobs_updated": "updated"}.get(value, value)


def _safe_host_path(url: str) -> str:
    match = re.match(r"^https://([^/]+)(/.+)$", url)
    return match.group(1) + match.group(2) if match else "weworkremotely.com"
