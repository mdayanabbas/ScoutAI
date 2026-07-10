import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.jobs.enrichment.models import JobDetailExtractionResult, JobFieldValue
from app.jobs.enrichment.parsers.ashby_job_parser import AshbyJobParser
from app.jobs.enrichment.providers.ashby_models import AshbyPublicJobPosting
from app.jobs.enrichment.providers.ashby_public_job_client import AshbyPublicJobClient
from app.jobs.expansion.hiring_scope_detector import HiringScopeDetector, HiringScopeResult
from app.jobs.expansion.models import (
    AshbyBoardExpansionCandidate,
    AshbyBoardExpansionResult,
)
from app.jobs.job_source_detector import JobSourceDetector, parse_ashby_job_url
from app.models.job import Job
from app.models.job_enrichment_attempt import JobEnrichmentAttempt
from app.repositories.job_board_expansion_link_repository import (
    JobBoardExpansionLinkRepository,
)
from app.repositories.job_discovery_link_repository import JobDiscoveryLinkRepository
from app.repositories.job_enrichment_attempt_repository import JobEnrichmentAttemptRepository
from app.repositories.job_repository import JobRepository
from app.utils.enums import JobEnrichmentStatus, JobSourceType, JobStatus
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)

PROVIDER = "ashby_board_expansion"


class AshbyBoardExpansionService:
    def __init__(
        self,
        session: Session,
        *,
        client: AshbyPublicJobClient | None = None,
        parser: AshbyJobParser | None = None,
        scope_detector: HiringScopeDetector | None = None,
    ) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.attempt_repository = JobEnrichmentAttemptRepository(session)
        self.discovery_link_repository = JobDiscoveryLinkRepository(session)
        self.expansion_link_repository = JobBoardExpansionLinkRepository(session)
        self.source_detector = JobSourceDetector()
        self.client = client or AshbyPublicJobClient()
        self.parser = parser or AshbyJobParser()
        self.scope_detector = scope_detector or HiringScopeDetector()
        self.settings = get_settings()

    async def expand_job_board(self, job_id: str) -> AshbyBoardExpansionResult:
        parent = self.job_repository.get_by_id(job_id)
        if parent is None:
            raise NotFoundError("Job not found")
        detection = self.source_detector.detect(
            parent.job_url,
            company_domain=getattr(parent.company, "normalized_domain", None),
            source_platform=parent.source_platform,
        )
        if detection.source_type != JobSourceType.ASHBY_JOB_BOARD or not detection.board_slug:
            return self._skipped(parent, detection, "unsupported_job_source")
        parsed_board = parse_ashby_job_url(detection.canonical_url)
        if parsed_board is None or not parsed_board.board_level:
            return self._skipped(parent, detection, "exact_posting_should_use_job_enrichment")
        if parent.company_id is None:
            return self._skipped(parent, detection, "unresolved_company")
        if parent.status == JobStatus.INACTIVE and self.expansion_link_repository.list_children(parent.id):
            return self._skipped(parent, detection, "board_already_expanded")

        candidate_links = self.discovery_link_repository.list_by_job_id(parent.id)
        candidates = [link.discovery_candidate for link in candidate_links if link.discovery_candidate is not None]
        scope = self.scope_detector.detect(
            title=parent.title,
            description=parent.description,
            normalized_title=parent.normalized_title,
            role_category=str(parent.role_category) if parent.role_category else None,
            candidates=candidates,
        )
        if scope.specific_role:
            return self._skipped(parent, detection, "specific_role_should_use_job_enrichment", scope=scope)

        attempt = self.attempt_repository.create_attempt(
            JobEnrichmentAttempt(
                job_id=parent.id,
                provider=PROVIDER,
                status="running",
                source_url=detection.canonical_url,
                started_at=datetime.now(timezone.utc),
            )
        )
        try:
            board = await self.client.list_published_jobs(detection.board_slug)
            if board.reason:
                self.attempt_repository.mark_failed(attempt, board.reason)
                return AshbyBoardExpansionResult(
                    parent_job_id=parent.id,
                    company_id=parent.company_id,
                    board_slug=detection.board_slug,
                    status="failed",
                    reason=board.reason,
                    attempt_id=attempt.id,
                )
            listed = [posting for posting in board.jobs if _valid_listed_posting(posting, detection.board_slug)]
            if len(board.jobs) > self.settings.ASHBY_BOARD_EXPANSION_MAX_POSTINGS:
                return self._unresolved(
                    parent,
                    attempt,
                    detection.board_slug,
                    scope,
                    "ashby_expansion_board_too_large",
                    board.jobs,
                    listed,
                    [],
                )
            scored = [_score_posting(posting, scope, detection.board_slug) for posting in listed]
            selected = _select_candidates(
                scored,
                scope,
                min_score=self.settings.ASHBY_BOARD_EXPANSION_MIN_MATCH_SCORE,
                max_create=self.settings.ASHBY_BOARD_EXPANSION_MAX_CREATE,
                allow_broad=self.settings.ASHBY_BOARD_EXPANSION_ALLOW_BROAD_HIRING,
            )
            if scope.scope_type == "unknown":
                return self._unresolved(parent, attempt, detection.board_slug, scope, "ashby_expansion_scope_unknown", board.jobs, listed, scored)
            if not selected:
                return self._unresolved(parent, attempt, detection.board_slug, scope, "no_matching_ashby_job", board.jobs, listed, scored)

            created_ids: list[str] = []
            existing_ids: list[str] = []
            failed_ids: list[str] = []
            output_candidates: list[AshbyBoardExpansionCandidate] = []
            for candidate_score in selected:
                posting = next(item for item in listed if item.id == candidate_score.posting_id)
                try:
                    parsed = self.parser.parse_posting(posting, board_slug=detection.board_slug)
                    if not parsed.success or parsed.job_url is None:
                        failed_ids.append(posting.id or "")
                        output_candidates.append(_candidate_with_status(candidate_score, "failed", "parse_failed"))
                        continue
                    job, action = self._create_or_reuse_child(parent, parsed, candidates)
                    self.expansion_link_repository.get_or_create_link(
                        parent_job_id=parent.id,
                        child_job_id=job.id,
                        discovery_candidate_id=candidates[0].id if candidates else None,
                        provider=PROVIDER,
                    )
                    if action == "created":
                        created_ids.append(job.id)
                    else:
                        existing_ids.append(job.id)
                    output_candidates.append(_candidate_with_job(candidate_score, job, action))
                    logger.info("Ashby expansion child processed", extra={"job_id": job.id, "action": action})
                except Exception as exc:
                    self.session.rollback()
                    failed_ids.append(candidate_score.posting_id or "")
                    output_candidates.append(_candidate_with_status(candidate_score, "failed", exc.__class__.__name__))

            succeeded = len(created_ids) + len(existing_ids)
            parent_deactivated = False
            if succeeded:
                self.job_repository.update_job(
                    parent,
                    {"status": JobStatus.INACTIVE, "last_verified_at": datetime.now(timezone.utc)},
                )
                parent_deactivated = True
            status = "succeeded" if succeeded and not failed_ids else "partial" if succeeded else "failed"
            result = AshbyBoardExpansionResult(
                parent_job_id=parent.id,
                company_id=parent.company_id,
                board_slug=detection.board_slug,
                status=status,
                reason="ashby_board_expanded" if status == "succeeded" else "ashby_board_expansion_partial",
                postings_seen=len(board.jobs),
                postings_listed=len(listed),
                postings_selected=len(selected),
                jobs_created=len(created_ids),
                jobs_existing=len(existing_ids),
                jobs_failed=len(failed_ids),
                parent_deactivated=parent_deactivated,
                created_job_ids=created_ids,
                existing_job_ids=existing_ids,
                candidates=output_candidates + [item for item in scored if item.posting_id not in {c.posting_id for c in output_candidates}][:20],
                attempt_id=attempt.id,
            )
            evidence = _evidence(scope, result, scored, failed_ids)
            if status == "succeeded":
                self.attempt_repository.mark_succeeded(attempt, reason=result.reason, evidence=evidence)
            elif status == "partial":
                self.attempt_repository.mark_partial(attempt, reason=result.reason, evidence=evidence)
            else:
                self.attempt_repository.mark_failed(attempt, "ashby_board_expansion_failed")
            return result
        except Exception as exc:
            self.session.rollback()
            attempt = self.attempt_repository.get_by_id(attempt.id) or attempt
            self.attempt_repository.mark_failed(attempt, "ashby_board_expansion_failed")
            logger.info("Ashby board expansion failed", extra={"job_id": parent.id, "error": exc.__class__.__name__})
            return AshbyBoardExpansionResult(
                parent_job_id=parent.id,
                company_id=parent.company_id,
                board_slug=detection.board_slug,
                status="failed",
                reason="ashby_board_expansion_failed",
                attempt_id=attempt.id,
            )

    def _create_or_reuse_child(
        self,
        parent: Job,
        parsed: JobDetailExtractionResult,
        candidates: list[Any],
    ) -> tuple[Job, str]:
        canonical_url = parsed.job_url.value if parsed.job_url else parsed.canonical_url
        existing = self.job_repository.get_by_company_and_url(parent.company_id, canonical_url)
        now = datetime.now(timezone.utc)
        if existing is not None:
            self.job_repository.update_job(existing, {"last_seen_at": now, "last_verified_at": now})
            for candidate in candidates:
                self.discovery_link_repository.get_or_create_link(existing.id, candidate.id)
            return existing, "existing"
        values = _job_values_from_parsed(parent.company_id, parsed, now)
        job = self.job_repository.create_job(Job(**values))
        for candidate in candidates:
            self.discovery_link_repository.get_or_create_link(job.id, candidate.id)
        return job, "created"

    def _skipped(
        self,
        parent: Job,
        detection: Any,
        reason: str,
        *,
        scope: HiringScopeResult | None = None,
    ) -> AshbyBoardExpansionResult:
        attempt = self.attempt_repository.create_attempt(
            JobEnrichmentAttempt(
                job_id=parent.id,
                provider=PROVIDER,
                status="running",
                source_url=getattr(detection, "canonical_url", None),
                started_at=datetime.now(timezone.utc),
            )
        )
        evidence = {
            "board_slug": getattr(detection, "board_slug", None),
            "scope": {
                "scope_type": scope.scope_type,
                "confidence": scope.confidence,
                "specific_role": scope.specific_role,
                "broad_hiring": scope.broad_hiring,
                "reason": scope.reason,
            }
            if scope
            else None,
        }
        self.attempt_repository.mark_skipped(attempt, reason=reason, evidence=evidence)
        return AshbyBoardExpansionResult(
            parent_job_id=parent.id,
            company_id=parent.company_id,
            board_slug=getattr(detection, "board_slug", None),
            status="skipped",
            reason=reason,
            warnings=[],
            attempt_id=attempt.id,
        )

    def _unresolved(
        self,
        parent: Job,
        attempt: JobEnrichmentAttempt,
        board_slug: str,
        scope: HiringScopeResult,
        reason: str,
        postings: list[AshbyPublicJobPosting],
        listed: list[AshbyPublicJobPosting],
        scored: list[AshbyBoardExpansionCandidate],
    ) -> AshbyBoardExpansionResult:
        result = AshbyBoardExpansionResult(
            parent_job_id=parent.id,
            company_id=parent.company_id,
            board_slug=board_slug,
            status="unresolved",
            reason=reason,
            postings_seen=len(postings),
            postings_listed=len(listed),
            candidates=scored[:20],
            attempt_id=attempt.id,
        )
        self.attempt_repository.mark_unresolved(attempt, reason=reason, evidence=_evidence(scope, result, scored, []))
        return result


def _valid_listed_posting(posting: AshbyPublicJobPosting, board_slug: str) -> bool:
    return bool(posting.is_listed is not False and posting.id and posting.title and _canonical_url(posting, board_slug))


def _score_posting(
    posting: AshbyPublicJobPosting,
    scope: HiringScopeResult,
    board_slug: str,
) -> AshbyBoardExpansionCandidate:
    text = " ".join(str(item or "") for item in (posting.title, posting.department, posting.team)).lower()
    matched: list[str] = []
    rejected: list[str] = []
    score = 0.0
    if scope.broad_hiring:
        score = 1.0
        matched.append("broad_hiring")
    else:
        for term in scope.department_terms:
            if term in (posting.department or "").lower():
                score += 0.4
                matched.append(f"department:{term}")
        for term in scope.team_terms:
            if term in (posting.team or "").lower():
                score += 0.3
                matched.append(f"team:{term}")
        for term in scope.title_terms:
            if term in text:
                score += 0.35
                matched.append(f"title:{term}")
        category = _category_for_posting(posting)
        if category in scope.role_categories:
            score += 0.25
            matched.append(f"role_category:{category}")
        elif scope.role_categories and category != "other":
            score -= 0.25
            rejected.append(f"conflicting_role_category:{category}")
    score = max(0.0, min(1.0, score))
    selected = False
    rejection = None if score else "no_matching_scope_signal"
    return AshbyBoardExpansionCandidate(
        posting_id=posting.id,
        title=posting.title,
        canonical_job_url=_canonical_url(posting, board_slug),
        apply_url=posting.apply_url,
        department=posting.department,
        team=posting.team,
        location=posting.location,
        employment_type=posting.employment_type,
        match_score=round(score, 3),
        matched_signals=matched[:10],
        rejected_signals=rejected[:10],
        selected=selected,
        rejection_reason=rejection,
    )


def _select_candidates(
    scored: list[AshbyBoardExpansionCandidate],
    scope: HiringScopeResult,
    *,
    min_score: float,
    max_create: int,
    allow_broad: bool,
) -> list[AshbyBoardExpansionCandidate]:
    if scope.broad_hiring and not allow_broad:
        return []
    if scope.broad_hiring:
        return [_selected(item) for item in scored[:max_create] if item.canonical_job_url]
    selected = [
        _selected(item)
        for item in sorted(scored, key=lambda item: (-item.match_score, item.title or ""))
        if item.match_score >= min_score and item.canonical_job_url
    ]
    return selected[:max_create]


def _selected(item: AshbyBoardExpansionCandidate) -> AshbyBoardExpansionCandidate:
    return AshbyBoardExpansionCandidate(**{**item.__dict__, "selected": True, "rejection_reason": None})


def _candidate_with_job(item: AshbyBoardExpansionCandidate, job: Job, action: str) -> AshbyBoardExpansionCandidate:
    return AshbyBoardExpansionCandidate(
        **{
            **item.__dict__,
            "job_id": job.id,
            "action": action,
            "status": "succeeded",
            "role_category": str(job.role_category) if job.role_category else None,
            "remote_type": str(job.remote_type) if job.remote_type else None,
        }
    )


def _candidate_with_status(item: AshbyBoardExpansionCandidate, status: str, reason: str) -> AshbyBoardExpansionCandidate:
    return AshbyBoardExpansionCandidate(**{**item.__dict__, "status": status, "rejection_reason": reason})


def _job_values_from_parsed(company_id: str, parsed: JobDetailExtractionResult, now: datetime) -> dict[str, Any]:
    title = _value(parsed.title) or "Untitled Ashby Job"
    return {
        "company_id": company_id,
        "discovery_candidate_id": None,
        "title": title,
        "normalized_title": normalize_title(title),
        "role_category": _value(parsed.role_category),
        "description": _value(parsed.description),
        "location": _value(parsed.location),
        "remote_type": _value(parsed.remote_type),
        "employment_type": _value(parsed.employment_type),
        "experience_min": _value(parsed.experience_min),
        "experience_max": _value(parsed.experience_max),
        "salary_min": _value(parsed.salary_min),
        "salary_max": _value(parsed.salary_max),
        "salary_currency": _value(parsed.salary_currency),
        "salary_text": _value(parsed.salary_text),
        "equity_mentioned": _value(parsed.equity_mentioned),
        "apply_url": _value(parsed.apply_url),
        "published_at": _value(parsed.published_at),
        "required_skills_json": _value(parsed.required_skills),
        "preferred_skills_json": _value(parsed.preferred_skills),
        "technologies_json": _value(parsed.technologies),
        "job_url": _value(parsed.job_url) or parsed.canonical_url,
        "source_platform": "ashby",
        "status": JobStatus.ACTIVE,
        "enrichment_status": JobEnrichmentStatus.ENRICHED if parsed.success else JobEnrichmentStatus.PARTIALLY_ENRICHED,
        "enrichment_confidence": parsed.evidence.get("overall_confidence"),
        "enriched_at": now,
        "last_verified_at": now,
        "first_seen_at": _value(parsed.published_at) or now,
        "last_seen_at": now,
    }


def _value(field: JobFieldValue | None) -> Any:
    return field.value if field is not None else None


def _canonical_url(posting: AshbyPublicJobPosting, board_slug: str) -> str | None:
    if posting.job_url:
        parsed = parse_ashby_job_url(posting.job_url)
        if parsed and parsed.exact_posting:
            return parsed.canonical_url
    if posting.id:
        return f"https://jobs.ashbyhq.com/{board_slug}/{posting.id}"
    return None


def _category_for_posting(posting: AshbyPublicJobPosting) -> str:
    from app.jobs.enrichment.parsers.ycombinator_job_parser import classify_role_category

    return classify_role_category(posting.title, " ".join(item for item in (posting.department, posting.team) if item), posting.description_plain)


def _evidence(
    scope: HiringScopeResult,
    result: AshbyBoardExpansionResult,
    scored: list[AshbyBoardExpansionCandidate],
    failed_ids: list[str],
) -> dict[str, Any]:
    return {
        "board_slug": result.board_slug,
        "scope": {
            "scope_type": scope.scope_type,
            "confidence": scope.confidence,
            "specific_role": scope.specific_role,
            "broad_hiring": scope.broad_hiring,
            "reason": scope.reason,
        },
        "postings_seen": result.postings_seen,
        "postings_listed": result.postings_listed,
        "postings_selected": result.postings_selected,
        "created_job_ids": result.created_job_ids,
        "existing_job_ids": result.existing_job_ids,
        "failed_posting_ids": failed_ids,
        "parent_deactivated": result.parent_deactivated,
        "candidate_scores": [
            {
                "posting_id": item.posting_id,
                "title": item.title,
                "score": item.match_score,
                "selected": item.selected,
                "matched_signals": item.matched_signals,
                "rejected_signals": item.rejected_signals,
            }
            for item in scored[:25]
        ],
    }
