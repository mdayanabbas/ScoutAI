import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.jobs.enrichment.models import JobDetailExtractionResult, JobFieldValue
from app.jobs.enrichment.parsers.ycombinator_job_parser import is_generic_job_title
from app.jobs.enrichment.providers.ashby_job_provider import (
    PROVIDER_NAME as ASHBY_PROVIDER_NAME,
    AshbyJobEnrichmentProvider,
)
from app.jobs.enrichment.providers.first_party_job_provider import (
    PROVIDER_NAME as FIRST_PARTY_PROVIDER_NAME,
    FirstPartyJobEnrichmentProvider,
)
from app.jobs.enrichment.providers.ycombinator_job_provider import (
    PROVIDER_NAME,
    YCombinatorJobEnrichmentProvider,
)
from app.jobs.job_source_detector import JobSourceDetector, normalize_job_url, parse_ashby_job_url, parse_yc_job_url
from app.models.job import Job
from app.models.job_enrichment_attempt import JobEnrichmentAttempt
from app.repositories.job_enrichment_attempt_repository import (
    JobEnrichmentAttemptRepository,
)
from app.repositories.job_repository import JobRepository
from app.utils.enums import JobEnrichmentStatus, JobSourceType
from app.utils.text import (
    clean_text_list,
    clean_text_value,
    normalize_title,
    repair_mojibake,
    should_replace_job_title,
    strip_job_title_action_suffix,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobEnrichmentResult:
    job_id: str
    status: str
    provider: str | None = None
    attempt_id: str | None = None
    reason: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    canonical_url: str | None = None
    updated_fields: dict[str, Any] = field(default_factory=dict)
    preserved_fields: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    enrichment_confidence: float | None = None


class JobDetailEnrichmentService:
    def __init__(
        self,
        session: Session,
        *,
        source_detector: JobSourceDetector | None = None,
        yc_provider: YCombinatorJobEnrichmentProvider | None = None,
        ashby_provider: AshbyJobEnrichmentProvider | None = None,
        first_party_provider: FirstPartyJobEnrichmentProvider | None = None,
    ) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.attempt_repository = JobEnrichmentAttemptRepository(session)
        self.source_detector = source_detector or JobSourceDetector()
        self.yc_provider = yc_provider or YCombinatorJobEnrichmentProvider()
        self.ashby_provider = ashby_provider or AshbyJobEnrichmentProvider()
        self.first_party_provider = first_party_provider or FirstPartyJobEnrichmentProvider()

    async def enrich_job(self, job_id: str) -> JobEnrichmentResult:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        company_domain = getattr(job.company, "normalized_domain", None)
        detection = self.source_detector.detect(
            job.job_url,
            company_domain=company_domain,
            source_platform=job.source_platform,
        )
        if detection.source_type == JobSourceType.YCOMBINATOR_JOB and detection.canonical_url:
            provider_name = PROVIDER_NAME
            provider = self.yc_provider
            provider_label = "YC"
        elif detection.source_type == JobSourceType.ASHBY_JOB_BOARD and detection.canonical_url:
            provider_name = ASHBY_PROVIDER_NAME
            provider = self.ashby_provider
            provider_label = "Ashby"
        elif detection.source_type == JobSourceType.FIRST_PARTY_JOB_PAGE and detection.canonical_url:
            provider_name = FIRST_PARTY_PROVIDER_NAME
            provider = self.first_party_provider
            provider_label = "First-party"
        else:
            return JobEnrichmentResult(
                job_id=job.id,
                status="skipped",
                reason="unsupported_provider_for_current_brick",
                source_type=detection.source_type.value,
                source_url=job.job_url,
                canonical_url=detection.canonical_url,
            )

        logger.info(f"{provider_label} enrichment started", extra={"job_id": job.id})
        attempt = self.attempt_repository.create_attempt(
            JobEnrichmentAttempt(
                job_id=job.id,
                provider=provider_name,
                status="running",
                source_url=detection.canonical_url,
                started_at=datetime.now(timezone.utc),
            )
        )
        try:
            if provider_name in {ASHBY_PROVIDER_NAME, FIRST_PARTY_PROVIDER_NAME}:
                parsed = await provider.enrich(detection, job=job)
            else:
                parsed = await provider.enrich(detection)
            if not parsed.success:
                evidence = _bounded_evidence(parsed, {}, {}, job)
                if parsed.reason in UNRESOLVED_REASONS:
                    self.job_repository.update_enrichment_fields(
                        job.id,
                        {
                            "enrichment_status": JobEnrichmentStatus.UNRESOLVED.value,
                            "last_verified_at": datetime.now(timezone.utc),
                        },
                    )
                    completed = self.attempt_repository.mark_unresolved(
                        attempt,
                        reason=parsed.reason or "yc_job_data_missing",
                        evidence=evidence,
                    )
                    return JobEnrichmentResult(
                        job.id,
                        "unresolved",
                        provider_name,
                        completed.id,
                        parsed.reason,
                        detection.source_type.value,
                        detection.canonical_url,
                        detection.canonical_url,
                        warnings=parsed.warnings,
                        enrichment_confidence=parsed.evidence.get("overall_confidence"),
                    )
                completed = self.attempt_repository.mark_failed(
                    attempt,
                    parsed.reason or "yc_job_page_fetch_failed",
                )
                self.job_repository.mark_enrichment_failed(job.id)
                return JobEnrichmentResult(
                    job.id,
                    "failed",
                    provider_name,
                    completed.id,
                    parsed.reason,
                    detection.source_type.value,
                    detection.canonical_url,
                    detection.canonical_url,
                    warnings=parsed.warnings,
                    enrichment_confidence=parsed.evidence.get("overall_confidence"),
                )

            updates, preserved = _build_safe_updates(job, parsed)
            status = _status_for(parsed, updates)
            updates["enrichment_status"] = status
            updates["enrichment_confidence"] = parsed.evidence.get("overall_confidence")
            updates["last_verified_at"] = datetime.now(timezone.utc)
            if _meaningful_update_fields(updates):
                updates["enriched_at"] = datetime.now(timezone.utc)
            updated_job = self.job_repository.update_enrichment_fields(job.id, updates)
            evidence = _bounded_evidence(parsed, updates, preserved, job)
            if status == JobEnrichmentStatus.ENRICHED.value:
                completed = self.attempt_repository.mark_succeeded(
                    attempt,
                    reason=parsed.reason,
                    extracted_data=parsed.extracted_data(),
                    evidence=evidence,
                    field_confidence=parsed.field_confidence,
                )
                logger.info(
                    f"{provider_label} enrichment succeeded",
                    extra={"job_id": job.id, "updated_fields": sorted(updates)},
                )
            else:
                completed = self.attempt_repository.mark_partial(
                    attempt,
                    reason=parsed.reason,
                    extracted_data=parsed.extracted_data(),
                    evidence=evidence,
                    field_confidence=parsed.field_confidence,
                )
                logger.info(
                    f"{provider_label} enrichment partial",
                    extra={"job_id": job.id, "updated_fields": sorted(updates)},
                )
            return JobEnrichmentResult(
                job_id=updated_job.id,
                status=status,
                provider=provider_name,
                attempt_id=completed.id,
                reason=parsed.reason,
                source_type=detection.source_type.value,
                source_url=detection.canonical_url,
                canonical_url=detection.canonical_url,
                updated_fields={key: _jsonable(getattr(updated_job, key)) for key in updates},
                preserved_fields=preserved,
                warnings=parsed.warnings,
                enrichment_confidence=parsed.evidence.get("overall_confidence"),
            )
        except Exception as exc:
            self.session.rollback()
            logger.info(
                f"{provider_label} enrichment failed",
                extra={"job_id": job.id, "error": exc.__class__.__name__},
            )
            attempt = self.attempt_repository.get_by_id(attempt.id) or attempt
            completed = self.attempt_repository.mark_failed(
                attempt,
                _safe_error_message(exc),
            )
            self.job_repository.mark_enrichment_failed(job.id)
            return JobEnrichmentResult(
                job.id,
                "failed",
                provider_name,
                completed.id,
                _update_failed_reason(provider_name),
                detection.source_type.value,
                detection.canonical_url,
                detection.canonical_url,
            )


UNRESOLVED_REASONS = {
    "yc_job_data_missing",
    "yc_job_invalid_html",
    "yc_job_parser_error",
    "ashby_no_published_jobs",
    "ashby_posting_not_found",
    "ambiguous_ashby_posting_match",
    "ambiguous_ashby_job_matches",
    "no_matching_ashby_job",
    "ashby_board_requires_job_matching",
    "ashby_job_data_missing",
    "first_party_listing_page_requires_expansion",
    "first_party_company_identity_mismatch",
    "first_party_job_data_missing",
}


def _update_failed_reason(provider_name: str) -> str:
    if provider_name == ASHBY_PROVIDER_NAME:
        return "ashby_update_failed"
    if provider_name == FIRST_PARTY_PROVIDER_NAME:
        return "first_party_update_failed"
    return "yc_job_update_failed"


def _build_safe_updates(
    job: Job, parsed: JobDetailExtractionResult
) -> tuple[dict[str, Any], dict[str, str]]:
    updates: dict[str, Any] = {}
    preserved: dict[str, str] = {}

    def maybe_set(field: str, value: JobFieldValue | None, *, min_confidence: float = 0.75) -> None:
        if value is None or value.confidence < min_confidence:
            if value is not None:
                preserved[field] = "extracted_confidence_too_low"
            return
        new_value = _clean_update_value(field, value.value)
        current = getattr(job, field)
        if current in (None, "", [], "unknown"):
            updates[field] = new_value
        elif _should_repair_existing_value(field, current, new_value):
            updates[field] = new_value
        else:
            preserved[field] = "existing_value_present"

    title = parsed.title
    if title and should_replace_job_title(job.title, title.value, title.confidence, title.source):
        clean_title = strip_job_title_action_suffix(str(title.value)) or str(title.value)
        updates["title"] = clean_title
        updates["normalized_title"] = normalize_title(clean_title)
        logger.info("Job title replaced with verified provider title", extra={"job_id": job.id})
    elif title and title.confidence >= 0.9:
        clean_title = strip_job_title_action_suffix(str(title.value)) or str(title.value)
        if job.title != clean_title:
            preserved["title"] = "existing_precise_title_preserved"
    elif title and title.confidence < 0.9:
        preserved["title"] = "weak_title_preserved"

    if parsed.description:
        current_description = job.description or ""
        new_description = repair_mojibake(str(parsed.description.value)) or str(parsed.description.value)
        if _should_replace_description(current_description, new_description):
            updates["description"] = new_description
        else:
            preserved["description"] = "existing_description_richer_or_equal"

    if parsed.job_url and parsed.job_url.confidence >= 0.9:
        current_ashby = parse_ashby_job_url(job.job_url)
        parsed_ashby = parse_ashby_job_url(parsed.job_url.value)
        parsed_yc = parse_yc_job_url(parsed.job_url.value)
        parsed_normalized = normalize_job_url(parsed.job_url.value)
        if (
            current_ashby
            and current_ashby.board_level
            and parsed_ashby
            and parsed_ashby.exact_posting
        ):
            updates["job_url"] = parsed_ashby.canonical_url
        elif current_ashby and current_ashby.exact_posting:
            preserved["job_url"] = "existing_exact_posting_url_preserved"
        elif parsed_ashby and parsed_ashby.exact_posting:
            updates["job_url"] = parsed_ashby.canonical_url
        elif parsed_yc:
            if job.job_url != parsed_yc.canonical_url:
                updates["job_url"] = parsed_yc.canonical_url
        elif parsed_normalized.valid and parsed_normalized.canonical_url and job.job_url != parsed_normalized.canonical_url:
            updates["job_url"] = parsed_normalized.canonical_url
        elif parsed_ashby:
            preserved["job_url"] = "existing_non_board_url_preserved"

    if parsed.role_category and parsed.role_category.confidence >= 0.9:
        if job.role_category in (None, "", "unknown") or job.role_category != parsed.role_category.value:
            updates["role_category"] = parsed.role_category.value
    elif parsed.role_category:
        preserved["role_category"] = "classifier_confidence_too_low"

    for field_name, parsed_field, minimum in (
        ("seniority", parsed.seniority, 0.8),
        ("location", parsed.location, 0.8),
        ("remote_type", parsed.remote_type, 0.8),
        ("employment_type", parsed.employment_type, 0.8),
        ("experience_min", parsed.experience_min, 0.8),
        ("experience_max", parsed.experience_max, 0.8),
        ("salary_min", parsed.salary_min, 0.8),
        ("salary_max", parsed.salary_max, 0.8),
        ("salary_currency", parsed.salary_currency, 0.8),
        ("salary_text", parsed.salary_text, 0.7),
        ("equity_mentioned", parsed.equity_mentioned, 0.8),
        ("apply_url", parsed.apply_url, 0.7),
        ("visa_sponsorship", parsed.visa_sponsorship, 0.8),
        ("work_authorization", parsed.work_authorization, 0.8),
        ("published_at", parsed.published_at, 0.8),
    ):
        maybe_set(field_name, parsed_field, min_confidence=minimum)

    if parsed.required_skills and (not job.required_skills_json or _should_replace_list(job.required_skills_json, parsed.required_skills.value)):
        updates["required_skills_json"] = clean_text_list(parsed.required_skills.value) or parsed.required_skills.value
    elif parsed.required_skills:
        preserved["required_skills_json"] = "existing_value_present"
    if parsed.preferred_skills and (not job.preferred_skills_json or _should_replace_list(job.preferred_skills_json, parsed.preferred_skills.value)):
        updates["preferred_skills_json"] = clean_text_list(parsed.preferred_skills.value) or parsed.preferred_skills.value
    elif parsed.preferred_skills:
        preserved["preferred_skills_json"] = "existing_value_present"
    if parsed.technologies and (not job.technologies_json or _should_replace_list(job.technologies_json, parsed.technologies.value)):
        updates["technologies_json"] = clean_text_list(parsed.technologies.value) or parsed.technologies.value
    elif parsed.technologies:
        preserved["technologies_json"] = "existing_value_present"
    return updates, preserved


def _status_for(parsed: JobDetailExtractionResult, updates: dict[str, Any]) -> str:
    important = {"title", "description", "role_category", "employment_type", "location"}
    extracted_important = important & set(parsed.field_confidence)
    if {"title", "role_category"} <= extracted_important and len(extracted_important) >= 3:
        return JobEnrichmentStatus.ENRICHED.value
    if updates:
        return JobEnrichmentStatus.PARTIALLY_ENRICHED.value
    return JobEnrichmentStatus.UNRESOLVED.value


def _meaningful_update_fields(updates: dict[str, Any]) -> bool:
    ignored = {"enrichment_status", "enrichment_confidence", "last_verified_at", "enriched_at"}
    return bool(set(updates) - ignored)


def _should_replace_description(current: str, new: str) -> bool:
    if not new or len(new) < 80:
        return False
    if _has_mojibake(current) and not _has_mojibake(new):
        return True
    if not current or len(current) < 200:
        return True
    return len(new) > len(current) * 1.4


def _clean_update_value(field: str, value: Any) -> Any:
    if field in {"location", "salary_text", "work_authorization"}:
        return clean_text_value(value)
    return value


def _should_repair_existing_value(field: str, current: Any, new: Any) -> bool:
    if new in (None, "", []):
        return False
    if field in {"location", "salary_text", "work_authorization"}:
        current_text = str(current or "")
        new_text = str(new or "")
        if _has_mojibake(current_text) and not _has_mojibake(new_text):
            return True
        if field == "work_authorization" and _polluted_authorization(current_text) and not _polluted_authorization(new_text):
            return True
    return False


def _should_replace_list(current: Any, new: Any) -> bool:
    current_list = current if isinstance(current, list) else []
    new_list = clean_text_list(new if isinstance(new, list) else []) or []
    if not new_list:
        return False
    if any(_has_mojibake(str(item)) for item in current_list) and not any(_has_mojibake(item) for item in new_list):
        return True
    current_fragments = sum(1 for item in current_list if len(str(item).split()) <= 1 and len(str(item)) <= 5)
    new_fragments = sum(1 for item in new_list if len(str(item).split()) <= 1 and len(str(item)) <= 5)
    return current_fragments > new_fragments and len(new_list) >= max(1, len(current_list) // 2)


def _has_mojibake(value: str) -> bool:
    repaired = repair_mojibake(value)
    return repaired != value


def _polluted_authorization(value: str) -> bool:
    lower = value.lower()
    return any(token in lower for token in ("open menu", "yc interview guide", "recommended jobs", "about y combinator"))


def _hn_sentence_title(value: str | None) -> bool:
    text = (value or "").lower()
    return " is hiring" in text or text.endswith("hiring")


def _bounded_evidence(
    parsed: JobDetailExtractionResult,
    updates: dict[str, Any],
    preserved: dict[str, str],
    job: Job | None = None,
) -> dict[str, Any]:
    evidence = dict(parsed.evidence)
    evidence.pop("raw_html", None)
    evidence["canonical_url"] = parsed.canonical_url
    evidence["warnings"] = parsed.warnings[:20]
    evidence["updated_fields"] = sorted(updates)
    evidence["preserved_fields"] = preserved
    evidence["field_confidence"] = parsed.field_confidence
    evidence["extracted_field_names"] = sorted(parsed.field_confidence)
    if job is not None and "job_url" in updates:
        evidence["job_url_change"] = {
            "previous": job.job_url,
            "new": updates["job_url"],
        }
    return evidence


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message if message else exc.__class__.__name__
