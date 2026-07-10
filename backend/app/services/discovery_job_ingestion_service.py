import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.discovery.hacker_news_job_parser import (
    ParsedHackerNewsJob,
    is_hacker_news_hiring_candidate,
    parse_hacker_news_job,
    role_category_for_title,
)
from app.jobs.job_source_detector import JobSourceDetector
from app.models.discovery_candidate import DiscoveryCandidate
from app.models.job import Job
from app.repositories.discovery_candidate_repository import DiscoveryCandidateRepository
from app.repositories.discovery_run_repository import DiscoveryRunRepository
from app.repositories.job_discovery_link_repository import JobDiscoveryLinkRepository
from app.repositories.job_repository import JobRepository
from app.schemas.discovery_job_ingestion import (
    DiscoveryJobIngestionResult,
    DiscoveryRunJobIngestionResult,
)
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    JobStatus,
    RemoteType,
)
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)


class DiscoveryJobIngestionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.candidate_repository = DiscoveryCandidateRepository(session)
        self.run_repository = DiscoveryRunRepository(session)
        self.job_repository = JobRepository(session)
        self.job_link_repository = JobDiscoveryLinkRepository(session)
        self.source_detector = JobSourceDetector()

    def ingest_candidate(self, candidate_id: str) -> DiscoveryJobIngestionResult:
        candidate = self._require_candidate(candidate_id)
        if not is_hacker_news_hiring_candidate(candidate):
            return self._skipped(candidate, "Candidate is not a Hacker News hiring post")
        if not self._is_resolved_candidate(candidate):
            return self._skipped(candidate, "Candidate does not have a resolved company")

        existing = self.job_repository.get_by_discovery_candidate_id(candidate.id)
        if existing is not None:
            self._ensure_job_link(existing, candidate)
            return self._already_exists(candidate, existing)

        parsed, ashby_metadata = self._parse_job(candidate)
        detected_source = self.source_detector.detect(parsed.job_url)
        normalized_job_url = (
            detected_source.canonical_url if detected_source.canonical_url else parsed.job_url
        )
        normalized_job_title = normalize_title(parsed.title) or parsed.title.lower()
        canonical = self.job_repository.get_legacy_match(
            candidate.matched_company_id,
            normalized_job_url,
            normalized_job_title,
        )
        if canonical is not None:
            values = {"last_seen_at": datetime.now(timezone.utc)}
            if canonical.discovery_candidate_id is None:
                values["discovery_candidate_id"] = candidate.id
            canonical = self.job_repository.update_job(canonical, values)
            self._ensure_job_link(canonical, candidate)
            return self._already_exists(candidate, canonical)

        url_existing = self.job_repository.get_by_company_and_url(
            candidate.matched_company_id, normalized_job_url
        )
        if url_existing is not None:
            values = {"last_seen_at": datetime.now(timezone.utc)}
            if url_existing.discovery_candidate_id is None:
                values["discovery_candidate_id"] = candidate.id
            url_existing = self.job_repository.update_job(url_existing, values)
            self._ensure_job_link(url_existing, candidate)
            return self._already_exists(candidate, url_existing)

        now = datetime.now(timezone.utc)
        job = self.job_repository.create_job(
            Job(
                company_id=candidate.matched_company_id,
                discovery_candidate_id=candidate.id,
                title=parsed.title,
                normalized_title=normalized_job_title,
                description=parsed.description,
                location=parsed.location,
                remote_type=parsed.remote_type,
                role_category=parsed.role_category,
                job_url=normalized_job_url,
                apply_url=self._normalized_optional_url((ashby_metadata or {}).get("apply_url")),
                source_platform="ashby" if ashby_metadata else "hacker_news",
                status=JobStatus.ACTIVE,
                first_seen_at=_ashby_published_at(ashby_metadata) or now,
                last_seen_at=now,
            )
        )
        self._ensure_job_link(job, candidate)
        return DiscoveryJobIngestionResult(
            candidate_id=candidate.id,
            company_id=candidate.matched_company_id,
            job_id=job.id,
            action="created",
            message="Created job from discovery candidate",
            job=job,
        )

    def ingest_discovery_run(
        self, run_id: str, limit: int | None = None
    ) -> DiscoveryRunJobIngestionResult:
        if self.run_repository.get_by_id(run_id) is None:
            raise NotFoundError("Discovery run not found")
        settings = get_settings()
        max_limit = min(
            limit or settings.DISCOVERY_JOB_INGESTION_MAX_CANDIDATES_PER_RUN,
            settings.DISCOVERY_JOB_INGESTION_MAX_CANDIDATES_PER_RUN,
        )
        candidates = [
            candidate
            for candidate in self.candidate_repository.list_by_run(
                run_id, limit=max_limit * 2
            )
            if is_hacker_news_hiring_candidate(candidate)
        ][:max_limit]

        results: list[DiscoveryJobIngestionResult] = []
        for candidate in candidates:
            try:
                results.append(self.ingest_candidate(candidate.id))
            except Exception as exc:
                self.session.rollback()
                logger.info(
                    "Discovery job ingestion failed",
                    extra={"candidate_id": candidate.id, "error": exc.__class__.__name__},
                )
                results.append(
                    DiscoveryJobIngestionResult(
                        candidate_id=candidate.id,
                        company_id=candidate.matched_company_id,
                        action="failed",
                        message=_safe_error_message(exc),
                    )
                )

        return DiscoveryRunJobIngestionResult(
            discovery_run_id=run_id,
            candidates_examined=len(candidates),
            jobs_created=sum(1 for result in results if result.action == "created"),
            jobs_existing=sum(
                1 for result in results if result.action == "already_exists"
            ),
            candidates_skipped=sum(1 for result in results if result.action == "skipped"),
            candidates_failed=sum(1 for result in results if result.action == "failed"),
            results=results,
        )

    def _parse_job(
        self, candidate: DiscoveryCandidate
    ) -> tuple[ParsedHackerNewsJob, dict | None]:
        fallback = parse_hacker_news_job(candidate)
        evidence = next(
            (
                item
                for item in candidate.evidence
                if item.evidence_type == "ashby_job_posting"
            ),
            None,
        )
        if evidence is None:
            return fallback, None
        metadata = evidence.metadata_json or {}
        title = evidence.title or fallback.title
        description = metadata.get("description_plain") or evidence.excerpt or fallback.description
        location = metadata.get("location") or fallback.location
        job_url = metadata.get("job_url") or metadata.get("apply_url") or evidence.source_url
        return (
            ParsedHackerNewsJob(
                title=title,
                description=description,
                location=location,
                remote_type=_ashby_remote_type(metadata, fallback.remote_type),
                role_category=role_category_for_title(title),
                job_url=job_url,
            ),
            metadata,
        )

    def _require_candidate(self, candidate_id: str) -> DiscoveryCandidate:
        candidate = self.candidate_repository.get_by_id(candidate_id)
        if candidate is None:
            raise NotFoundError("Discovery candidate not found")
        return candidate

    def _is_resolved_candidate(self, candidate: DiscoveryCandidate) -> bool:
        return (
            candidate.status == DiscoveryCandidateStatus.INGESTED
            and candidate.decision
            in {
                DiscoveryDecision.CREATED_COMPANY,
                DiscoveryDecision.MATCHED_EXISTING_COMPANY,
            }
            and candidate.matched_company_id is not None
        )

    def _skipped(
        self, candidate: DiscoveryCandidate, message: str
    ) -> DiscoveryJobIngestionResult:
        return DiscoveryJobIngestionResult(
            candidate_id=candidate.id,
            company_id=candidate.matched_company_id,
            action="skipped",
            message=message,
        )

    def _already_exists(
        self, candidate: DiscoveryCandidate, job: Job
    ) -> DiscoveryJobIngestionResult:
        return DiscoveryJobIngestionResult(
            candidate_id=candidate.id,
            company_id=candidate.matched_company_id,
            job_id=job.id,
            action="already_exists",
            message="Job already exists for discovery candidate",
            job=job,
        )

    def _ensure_job_link(self, job: Job, candidate: DiscoveryCandidate) -> None:
        self.job_link_repository.ensure_link(job.id, candidate.id)

    def _normalized_optional_url(self, value: str | None) -> str | None:
        if not value:
            return None
        detection = self.source_detector.detect(value)
        return detection.canonical_url if detection.canonical_url else value


def _ashby_remote_type(metadata: dict, fallback: RemoteType) -> RemoteType:
    workplace = str(metadata.get("workplace_type") or "").lower()
    if workplace in {"on-site", "onsite", "in-office"}:
        return RemoteType.ONSITE
    if workplace == "hybrid":
        return RemoteType.HYBRID
    if workplace == "remote" or metadata.get("is_remote") is True:
        return RemoteType.REMOTE_WORLDWIDE
    return fallback


def _ashby_published_at(metadata: dict | None) -> datetime | None:
    if not metadata or not isinstance(metadata.get("published_at"), str):
        return None
    try:
        return datetime.fromisoformat(metadata["published_at"].replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message if message else exc.__class__.__name__
