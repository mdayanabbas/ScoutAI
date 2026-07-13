import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.jobs.enrichment.models import JobDetailExtractionResult, JobFieldValue
from app.jobs.enrichment.parsers.first_party_job_parser import FirstPartyJobParser
from app.jobs.enrichment.parsers.ycombinator_job_parser import classify_role_category, is_generic_job_title
from app.jobs.enrichment.providers.first_party_job_client import FirstPartyJobClient
from app.jobs.expansion.first_party_listing_models import (
    FirstPartyListingCandidate,
    FirstPartyListingChild,
    FirstPartyListingExpansionResult,
)
from app.jobs.expansion.first_party_listing_parser import FirstPartyListingParser
from app.jobs.expansion.hiring_scope_detector import HiringScopeDetector, HiringScopeResult
from app.jobs.job_source_detector import JobSourceDetector, compare_registrable_domains, normalize_job_url, parse_ashby_job_url
from app.models.job import Job
from app.models.job_enrichment_attempt import JobEnrichmentAttempt
from app.repositories.job_board_expansion_link_repository import JobBoardExpansionLinkRepository
from app.repositories.job_discovery_link_repository import JobDiscoveryLinkRepository
from app.repositories.job_enrichment_attempt_repository import JobEnrichmentAttemptRepository
from app.repositories.job_repository import JobRepository
from app.utils.enums import JobEnrichmentStatus, JobSourceType, JobStatus
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)

PROVIDER = "first_party_listing_expansion"


class FirstPartyListingExpansionService:
    def __init__(
        self,
        session: Session,
        *,
        client: FirstPartyJobClient | None = None,
        listing_parser: FirstPartyListingParser | None = None,
        detail_parser: FirstPartyJobParser | None = None,
        scope_detector: HiringScopeDetector | None = None,
    ) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.attempt_repository = JobEnrichmentAttemptRepository(session)
        self.discovery_link_repository = JobDiscoveryLinkRepository(session)
        self.expansion_link_repository = JobBoardExpansionLinkRepository(session)
        self.source_detector = JobSourceDetector()
        self.client = client or FirstPartyJobClient()
        self.listing_parser = listing_parser or FirstPartyListingParser()
        self.detail_parser = detail_parser or FirstPartyJobParser()
        self.scope_detector = scope_detector or HiringScopeDetector()
        self.settings = get_settings()

    async def expand_listing(self, job_id: str) -> FirstPartyListingExpansionResult:
        parent = self.job_repository.get_by_id(job_id)
        if parent is None:
            raise NotFoundError("Job not found")
        company_domain = getattr(parent.company, "normalized_domain", None)
        detection = self.source_detector.detect(
            parent.job_url,
            company_domain=company_domain,
            source_platform=parent.source_platform,
        )
        if detection.source_type != JobSourceType.FIRST_PARTY_JOB_PAGE or not detection.canonical_url:
            return self._skipped(parent, detection, "unsupported_job_source")
        if parent.company_id is None:
            return self._skipped(parent, detection, "unresolved_company")
        if not company_domain:
            return self._skipped(parent, detection, "missing_company_domain")
        if parent.status == JobStatus.INACTIVE and self.expansion_link_repository.list_children(parent.id):
            return self._skipped(parent, detection, "listing_already_expanded")

        discovery_links = self.discovery_link_repository.list_by_job_id(parent.id)
        candidates = [link.discovery_candidate for link in discovery_links if link.discovery_candidate is not None]
        scope = self.scope_detector.detect(
            title=parent.title,
            description=parent.description,
            normalized_title=parent.normalized_title,
            role_category=str(parent.role_category) if parent.role_category else None,
            candidates=candidates,
        )
        logger.info("First-party listing hiring scope detected", extra={"job_id": parent.id, "scope_type": scope.scope_type})
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
            logger.info("First-party listing expansion requested", extra={"job_id": parent.id})
            page = await self.client.fetch_job_page(detection.canonical_url, company_domain=company_domain)
            if page.reason or not page.html:
                self.attempt_repository.mark_failed(attempt, page.reason or "first_party_listing_fetch_failed")
                logger.info("First-party listing expansion failed", extra={"job_id": parent.id, "reason": page.reason})
                return FirstPartyListingExpansionResult(
                    parent_job_id=parent.id,
                    company_id=parent.company_id,
                    status="failed",
                    reason=page.reason or "first_party_listing_fetch_failed",
                    attempt_id=attempt.id,
                    warnings=page.warnings,
                )
            canonical_url = page.final_url or detection.canonical_url
            logger.info("First-party listing fetched", extra={"job_id": parent.id, "response_size": page.response_size})
            extraction = self.listing_parser.parse(
                page.html,
                source_url=detection.canonical_url,
                canonical_url=canonical_url,
                company_name=getattr(parent.company, "name", None),
                company_domain=company_domain,
            )
            logger.info(
                "First-party listing parsed",
                extra={"job_id": parent.id, "candidate_count": extraction.candidate_count, "reason": extraction.reason},
            )
            exact = self.detail_parser.parse(
                page.html,
                source_url=detection.canonical_url,
                canonical_url=canonical_url,
                company_name=getattr(parent.company, "name", None),
                company_domain=company_domain,
            )
            if exact.success and not _has_multiple_listing_candidates(extraction):
                return self._complete_unresolved_or_skipped(
                    parent,
                    attempt,
                    scope,
                    "skipped",
                    "exact_page_should_use_job_enrichment",
                    extraction.candidates,
                    extraction.candidate_count,
                )
            if not extraction.listing_detected:
                if exact.success:
                    return self._complete_unresolved_or_skipped(
                        parent,
                        attempt,
                        scope,
                        "skipped",
                        "exact_page_should_use_job_enrichment",
                        extraction.candidates,
                        extraction.candidate_count,
                    )
                return self._complete_unresolved_or_skipped(
                    parent,
                    attempt,
                    scope,
                    "unresolved",
                    extraction.reason,
                    extraction.candidates,
                    extraction.candidate_count,
                )

            scored = [_score_candidate(item, scope) for item in extraction.candidates]
            selected = _select_candidates(scored, scope, self.settings)
            if scope.scope_type == "unknown" and not selected:
                return self._complete_unresolved_or_skipped(
                    parent,
                    attempt,
                    scope,
                    "unresolved",
                    "first_party_listing_scope_unknown",
                    scored,
                    extraction.candidate_count,
                )
            if not selected:
                return self._complete_unresolved_or_skipped(
                    parent,
                    attempt,
                    scope,
                    "unresolved",
                    "first_party_listing_no_safe_candidates",
                    scored,
                    extraction.candidate_count,
                )

            created_ids: list[str] = []
            existing_ids: list[str] = []
            failed: list[dict[str, str | None]] = []
            children: list[FirstPartyListingChild] = []
            output_candidates: list[FirstPartyListingCandidate] = []
            detail_fetches = 0
            for index, candidate in enumerate(selected):
                try:
                    parsed = None
                    source_platform = "ashby" if parse_ashby_job_url(candidate.canonical_url) else "first_party"
                    should_fetch = source_platform == "first_party" and bool(candidate.canonical_url)
                    if should_fetch and detail_fetches < self.settings.FIRST_PARTY_LISTING_MAX_DETAIL_FETCHES:
                        if detail_fetches and self.settings.FIRST_PARTY_LISTING_DELAY_MS:
                            await asyncio.sleep(self.settings.FIRST_PARTY_LISTING_DELAY_MS / 1000)
                        detail_page = await self.client.fetch_job_page(candidate.canonical_url or "", company_domain=company_domain)
                        detail_fetches += 1
                        logger.info("First-party detail page fetched", extra={"job_id": parent.id, "candidate_url": candidate.canonical_url, "reason": detail_page.reason})
                        if detail_page.html and not detail_page.reason:
                            detail_url = detail_page.final_url or candidate.canonical_url or canonical_url
                            if not compare_registrable_domains(normalize_job_url(detail_url).normalized_domain, company_domain):
                                parsed = None
                            else:
                                parsed = self.detail_parser.parse(
                                    detail_page.html,
                                    source_url=candidate.canonical_url or "",
                                    canonical_url=detail_url,
                                    company_name=getattr(parent.company, "name", None),
                                    company_domain=company_domain,
                                )
                    job, action = self._create_or_reuse_child(
                        parent,
                        candidate,
                        parsed,
                        source_platform=source_platform,
                        discovery_candidates=candidates,
                    )
                    self.expansion_link_repository.get_or_create_link(
                        parent_job_id=parent.id,
                        child_job_id=job.id,
                        discovery_candidate_id=candidates[0].id if candidates else None,
                        provider=PROVIDER,
                    )
                    logger.info("First-party expansion link created", extra={"parent_job_id": parent.id, "child_job_id": job.id})
                    if action == "created":
                        created_ids.append(job.id)
                        logger.info("First-party child created", extra={"job_id": job.id})
                    else:
                        existing_ids.append(job.id)
                        logger.info("First-party existing child reused", extra={"job_id": job.id})
                    children.append(_child_read(job, action))
                    output_candidates.append(_candidate_with_job(candidate, job, action))
                except Exception as exc:
                    self.session.rollback()
                    failed.append({"title": candidate.title, "canonical_url": candidate.canonical_url, "reason": exc.__class__.__name__})
                    output_candidates.append(_candidate_with_status(candidate, "failed", exc.__class__.__name__))
                    logger.info("First-party listing candidate failed", extra={"job_id": parent.id, "error": exc.__class__.__name__})

            succeeded = len(created_ids) + len(existing_ids)
            parent_deactivated = False
            if succeeded:
                self.job_repository.update_job(parent, {"status": JobStatus.INACTIVE, "last_verified_at": datetime.now(timezone.utc)})
                parent_deactivated = True
                logger.info("First-party listing parent deactivated", extra={"job_id": parent.id})
            status = "succeeded" if succeeded and not failed else "partial" if succeeded else "unresolved"
            reason = "first_party_listing_expanded" if status == "succeeded" else "first_party_listing_expansion_partial" if status == "partial" else "first_party_listing_child_creation_failed"
            result = FirstPartyListingExpansionResult(
                parent_job_id=parent.id,
                company_id=parent.company_id,
                status=status,
                reason=reason,
                links_seen=extraction.candidate_count,
                candidates_selected=len(selected),
                detail_pages_fetched=detail_fetches,
                jobs_created=len(created_ids),
                jobs_existing=len(existing_ids),
                jobs_failed=len(failed),
                parent_deactivated=parent_deactivated,
                created_job_ids=created_ids,
                existing_job_ids=existing_ids,
                failed_candidates=failed,
                children=children,
                candidates=output_candidates + [item for item in scored if item.canonical_url not in {c.canonical_url for c in output_candidates}][:20],
                warnings=page.warnings + extraction.warnings,
                attempt_id=attempt.id,
            )
            evidence = _evidence(scope, result)
            if status == "succeeded":
                self.attempt_repository.mark_succeeded(attempt, reason=reason, evidence=evidence)
                logger.info("First-party listing expansion succeeded", extra={"job_id": parent.id})
            elif status == "partial":
                self.attempt_repository.mark_partial(attempt, reason=reason, evidence=evidence)
                logger.info("First-party listing expansion partial", extra={"job_id": parent.id})
            else:
                self.attempt_repository.mark_unresolved(attempt, reason=reason, evidence=evidence)
                logger.info("First-party listing expansion unresolved", extra={"job_id": parent.id})
            return result
        except Exception as exc:
            self.session.rollback()
            attempt = self.attempt_repository.get_by_id(attempt.id) or attempt
            self.attempt_repository.mark_failed(attempt, "first_party_listing_expansion_failed")
            logger.info("First-party listing expansion failed", extra={"job_id": parent.id, "error": exc.__class__.__name__})
            return FirstPartyListingExpansionResult(
                parent_job_id=parent.id,
                company_id=parent.company_id,
                status="failed",
                reason="first_party_listing_expansion_failed",
                attempt_id=attempt.id,
            )

    def _create_or_reuse_child(
        self,
        parent: Job,
        candidate: FirstPartyListingCandidate,
        parsed: JobDetailExtractionResult | None,
        *,
        source_platform: str,
        discovery_candidates: list[Any],
    ) -> tuple[Job, str]:
        now = datetime.now(timezone.utc)
        canonical_url = _parsed_value(parsed.job_url) if parsed and parsed.success and parsed.job_url else candidate.canonical_url
        normalized_title = normalize_title(_parsed_value(parsed.title) if parsed and parsed.success and parsed.title else candidate.title or "")
        existing = self.job_repository.get_by_company_and_url(parent.company_id, canonical_url) if canonical_url else None
        if existing is None and candidate.posting_identifier:
            existing = self._find_by_identifier(parent.company_id, candidate.posting_identifier)
        if existing is None and not canonical_url and candidate.confidence >= 0.9 and normalized_title:
            existing = self._find_by_precise_title(parent.company_id, normalized_title)
        if existing is not None:
            self.job_repository.update_job(existing, {"last_seen_at": now, "last_verified_at": now})
            for discovery_candidate in discovery_candidates:
                self.discovery_link_repository.get_or_create_link(existing.id, discovery_candidate.id)
                logger.info("First-party provenance link created", extra={"job_id": existing.id, "candidate_id": discovery_candidate.id})
            return existing, "existing"

        values = _job_values(parent.company_id, candidate, parsed, now, source_platform)
        try:
            job = self.job_repository.create_job(Job(**values))
        except IntegrityError:
            self.session.rollback()
            existing = self.job_repository.get_by_company_and_url(parent.company_id, canonical_url) if canonical_url else None
            if existing is None:
                raise
            self.job_repository.update_job(existing, {"last_seen_at": now, "last_verified_at": now})
            return existing, "existing"
        for discovery_candidate in discovery_candidates:
            self.discovery_link_repository.get_or_create_link(job.id, discovery_candidate.id)
            logger.info("First-party provenance link created", extra={"job_id": job.id, "candidate_id": discovery_candidate.id})
        return job, "created"

    def _find_by_identifier(self, company_id: str, identifier: str) -> Job | None:
        pattern = f"%{identifier}%"
        stmt = select(Job).where(Job.company_id == company_id, Job.job_url.ilike(pattern))
        return self.session.scalar(stmt)

    def _find_by_precise_title(self, company_id: str, normalized_title: str) -> Job | None:
        stmt = select(Job).where(Job.company_id == company_id, Job.normalized_title == normalized_title)
        return self.session.scalar(stmt)

    def _skipped(
        self,
        parent: Job,
        detection: Any,
        reason: str,
        *,
        scope: HiringScopeResult | None = None,
    ) -> FirstPartyListingExpansionResult:
        attempt = self.attempt_repository.create_attempt(
            JobEnrichmentAttempt(
                job_id=parent.id,
                provider=PROVIDER,
                status="running",
                source_url=getattr(detection, "canonical_url", None),
                started_at=datetime.now(timezone.utc),
            )
        )
        self.attempt_repository.mark_skipped(attempt, reason=reason, evidence={"scope": _scope_evidence(scope)})
        return FirstPartyListingExpansionResult(
            parent_job_id=parent.id,
            company_id=parent.company_id,
            status="skipped",
            reason=reason,
            attempt_id=attempt.id,
        )

    def _complete_unresolved_or_skipped(
        self,
        parent: Job,
        attempt: JobEnrichmentAttempt,
        scope: HiringScopeResult,
        status: str,
        reason: str,
        candidates: list[FirstPartyListingCandidate],
        links_seen: int,
    ) -> FirstPartyListingExpansionResult:
        result = FirstPartyListingExpansionResult(
            parent_job_id=parent.id,
            company_id=parent.company_id,
            status=status,
            reason=reason,
            links_seen=links_seen,
            candidates=candidates[:20],
            attempt_id=attempt.id,
        )
        evidence = {"scope": _scope_evidence(scope), "candidate_scores": [_candidate_evidence(item) for item in candidates[:25]]}
        if status == "skipped":
            self.attempt_repository.mark_skipped(attempt, reason=reason, evidence=evidence)
        else:
            self.attempt_repository.mark_unresolved(attempt, reason=reason, evidence=evidence)
        return result


def _score_candidate(candidate: FirstPartyListingCandidate, scope: HiringScopeResult) -> FirstPartyListingCandidate:
    matched = list(candidate.matched_signals)
    rejected = list(candidate.rejected_signals)
    if candidate.rejection_reason:
        return candidate
    score = candidate.confidence
    if scope.broad_hiring:
        score = max(score, 1.0)
        matched.append("broad_hiring")
    elif scope.scope_type == "unknown":
        score = candidate.confidence if candidate.confidence >= 0.9 else 0.0
        if score:
            matched.append("single_unknown_scope_candidate_allowed")
        else:
            rejected.append("scope_unknown")
    else:
        role_category = classify_role_category(candidate.title, " ".join(item for item in (candidate.department, candidate.team) if item), candidate.description_excerpt)
        text = " ".join(str(item or "") for item in (candidate.title, candidate.department, candidate.team)).lower()
        scope_score = 0.0
        if role_category in scope.role_categories:
            scope_score += 0.45
            matched.append(f"role_category:{role_category}")
        elif scope.role_categories and role_category != "other":
            scope_score -= 0.3
            rejected.append(f"conflicting_role_category:{role_category}")
        for term in scope.department_terms:
            if term in (candidate.department or "").lower():
                scope_score += 0.25
                matched.append(f"department:{term}")
        for term in scope.team_terms:
            if term in (candidate.team or "").lower():
                scope_score += 0.2
                matched.append(f"team:{term}")
        for term in scope.title_terms:
            if term in text:
                scope_score += 0.25
                matched.append(f"title:{term}")
        score = max(0.0, min(1.0, (candidate.confidence * 0.55) + scope_score))
    return FirstPartyListingCandidate(
        **{
            **candidate.__dict__,
            "scope_score": round(score, 3),
            "matched_signals": matched[:10],
            "rejected_signals": rejected[:10],
            "rejection_reason": candidate.rejection_reason if score else "no_matching_scope_signal",
            "role_category": classify_role_category(candidate.title, candidate.department, candidate.description_excerpt),
        }
    )


def _select_candidates(candidates: list[FirstPartyListingCandidate], scope: HiringScopeResult, settings: Any) -> list[FirstPartyListingCandidate]:
    valid = [
        item
        for item in candidates
        if not item.rejection_reason
        and item.confidence >= settings.FIRST_PARTY_LISTING_MIN_LINK_CONFIDENCE
        and item.scope_score >= settings.FIRST_PARTY_LISTING_MIN_SCOPE_SCORE
        and not is_generic_job_title(item.title)
    ]
    if scope.broad_hiring:
        if not settings.FIRST_PARTY_LISTING_ALLOW_BROAD_HIRING:
            return []
        return [_selected(item) for item in valid[: settings.FIRST_PARTY_LISTING_MAX_CREATE]]
    if scope.scope_type == "unknown":
        return [_selected(valid[0])] if len(valid) == 1 else []
    return [_selected(item) for item in sorted(valid, key=lambda item: (-item.scope_score, item.title or ""))[: settings.FIRST_PARTY_LISTING_MAX_CREATE]]


def _has_multiple_listing_candidates(extraction: Any) -> bool:
    valid = [item for item in extraction.candidates if not item.rejection_reason]
    if len(valid) > 1:
        return True
    return extraction.reason == "first_party_listing_detected" and extraction.candidate_count > 1


def _selected(candidate: FirstPartyListingCandidate) -> FirstPartyListingCandidate:
    return FirstPartyListingCandidate(**{**candidate.__dict__, "selected": True, "rejection_reason": None})


def _candidate_with_job(candidate: FirstPartyListingCandidate, job: Job, action: str) -> FirstPartyListingCandidate:
    return FirstPartyListingCandidate(
        **{
            **candidate.__dict__,
            "job_id": job.id,
            "action": action,
            "status": "succeeded",
            "role_category": str(job.role_category) if job.role_category else None,
            "remote_type": str(job.remote_type) if job.remote_type else None,
        }
    )


def _candidate_with_status(candidate: FirstPartyListingCandidate, status: str, reason: str) -> FirstPartyListingCandidate:
    return FirstPartyListingCandidate(**{**candidate.__dict__, "status": status, "rejection_reason": reason})


def _job_values(
    company_id: str,
    candidate: FirstPartyListingCandidate,
    parsed: JobDetailExtractionResult | None,
    now: datetime,
    source_platform: str,
) -> dict[str, Any]:
    title = _parsed_value(parsed.title) if parsed and parsed.success and parsed.title else candidate.title
    if not title or is_generic_job_title(title):
        raise ValueError("missing_specific_title")
    description = _parsed_value(parsed.description) if parsed and parsed.success and parsed.description else candidate.description_excerpt
    role_category = _parsed_value(parsed.role_category) if parsed and parsed.success and parsed.role_category else classify_role_category(title, candidate.department, description)
    job_url = _parsed_value(parsed.job_url) if parsed and parsed.success and parsed.job_url else candidate.canonical_url
    if not job_url and not candidate.posting_identifier:
        raise ValueError("insufficient_child_identity")
    if not job_url:
        job_url = f"first-party://posting/{company_id}/{candidate.posting_identifier}"
    return {
        "company_id": company_id,
        "discovery_candidate_id": None,
        "title": title,
        "normalized_title": normalize_title(title),
        "role_category": role_category,
        "description": description,
        "location": _parsed_value(parsed.location) if parsed and parsed.success and parsed.location else candidate.location,
        "remote_type": _parsed_value(parsed.remote_type) if parsed and parsed.success and parsed.remote_type else None,
        "employment_type": _parsed_value(parsed.employment_type) if parsed and parsed.success and parsed.employment_type else candidate.employment_type,
        "experience_min": _parsed_value(parsed.experience_min) if parsed and parsed.success else None,
        "experience_max": _parsed_value(parsed.experience_max) if parsed and parsed.success else None,
        "salary_min": _parsed_value(parsed.salary_min) if parsed and parsed.success else None,
        "salary_max": _parsed_value(parsed.salary_max) if parsed and parsed.success else None,
        "salary_currency": _parsed_value(parsed.salary_currency) if parsed and parsed.success else None,
        "salary_text": _parsed_value(parsed.salary_text) if parsed and parsed.success else None,
        "equity_mentioned": _parsed_value(parsed.equity_mentioned) if parsed and parsed.success else None,
        "apply_url": _parsed_value(parsed.apply_url) if parsed and parsed.success and parsed.apply_url else None,
        "published_at": _parsed_value(parsed.published_at) if parsed and parsed.success else None,
        "visa_sponsorship": _parsed_value(parsed.visa_sponsorship) if parsed and parsed.success else None,
        "work_authorization": _parsed_value(parsed.work_authorization) if parsed and parsed.success else None,
        "required_skills_json": _parsed_value(parsed.required_skills) if parsed and parsed.success else None,
        "preferred_skills_json": _parsed_value(parsed.preferred_skills) if parsed and parsed.success else None,
        "technologies_json": _parsed_value(parsed.technologies) if parsed and parsed.success else None,
        "job_url": job_url,
        "source_platform": source_platform,
        "status": JobStatus.ACTIVE,
        "enrichment_status": JobEnrichmentStatus.ENRICHED if parsed and parsed.success else JobEnrichmentStatus.PARTIALLY_ENRICHED,
        "enrichment_confidence": (parsed.evidence or {}).get("overall_confidence") if parsed else candidate.confidence,
        "enriched_at": now if parsed and parsed.success else None,
        "last_verified_at": now,
        "first_seen_at": _parsed_value(parsed.published_at) if parsed and parsed.success and parsed.published_at else now,
        "last_seen_at": now,
    }


def _parsed_value(field: JobFieldValue | None) -> Any:
    return field.value if field else None


def _child_read(job: Job, action: str) -> FirstPartyListingChild:
    return FirstPartyListingChild(
        job_id=job.id,
        title=job.title,
        job_url=job.job_url,
        role_category=str(job.role_category) if job.role_category else None,
        location=job.location,
        remote_type=str(job.remote_type) if job.remote_type else None,
        action=action,
    )


def _scope_evidence(scope: HiringScopeResult | None) -> dict[str, Any] | None:
    if scope is None:
        return None
    return {
        "scope_type": scope.scope_type,
        "confidence": scope.confidence,
        "specific_role": scope.specific_role,
        "broad_hiring": scope.broad_hiring,
        "reason": scope.reason,
    }


def _candidate_evidence(candidate: FirstPartyListingCandidate) -> dict[str, Any]:
    return {
        "title": candidate.title,
        "canonical_url": candidate.canonical_url,
        "source_strategy": candidate.source_strategy,
        "confidence": candidate.confidence,
        "scope_score": candidate.scope_score,
        "selected": candidate.selected,
        "rejection_reason": candidate.rejection_reason,
        "matched_signals": candidate.matched_signals[:8],
        "rejected_signals": candidate.rejected_signals[:8],
    }


def _evidence(scope: HiringScopeResult, result: FirstPartyListingExpansionResult) -> dict[str, Any]:
    return {
        "scope": _scope_evidence(scope),
        "links_seen": result.links_seen,
        "candidates_selected": result.candidates_selected,
        "detail_pages_fetched": result.detail_pages_fetched,
        "created_job_ids": result.created_job_ids,
        "existing_job_ids": result.existing_job_ids,
        "failed_candidates": result.failed_candidates[:25],
        "parent_deactivated": result.parent_deactivated,
        "candidate_scores": [_candidate_evidence(item) for item in result.candidates[:25]],
    }
