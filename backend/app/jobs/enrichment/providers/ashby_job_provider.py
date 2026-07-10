import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.jobs.enrichment.models import JobDetailExtractionResult
from app.jobs.enrichment.parsers.ashby_job_parser import (
    AshbyJobParser,
    parse_ashby_posting_identifier,
)
from app.jobs.enrichment.parsers.ycombinator_job_parser import (
    classify_role_category,
    is_generic_job_title,
)
from app.jobs.enrichment.providers.ashby_models import AshbyPublicJobPosting
from app.jobs.enrichment.providers.ashby_public_job_client import AshbyPublicJobClient
from app.jobs.job_source_detector import normalize_job_url
from app.jobs.source_detection import JobSourceDetectionResult
from app.models.job import Job
from app.utils.enums import JobSourceType
from app.utils.text import normalize_title

logger = logging.getLogger(__name__)

PROVIDER_NAME = "ashby_public_job_board"
GENERIC_BOARD_TITLES = {
    "careers",
    "engineering team",
    "gtm team",
    "hiring",
    "is hiring",
    "jobs",
    "join our team",
    "multiple roles",
    "open roles",
    "software roles",
}
WEAK_TOKENS = {"hiring", "jobs", "job", "role", "roles", "team", "open", "join", "our", "is"}


@dataclass(frozen=True)
class AshbyPostingCandidateScore:
    posting_id: str | None
    title: str | None
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AshbyPostingMatchResult:
    selected_posting: AshbyPublicJobPosting | None
    confidence: float
    reason: str
    candidate_scores: list[AshbyPostingCandidateScore] = field(default_factory=list)
    ambiguity: bool = False
    warnings: list[str] = field(default_factory=list)


class AshbyJobEnrichmentProvider:
    provider_name = PROVIDER_NAME

    def __init__(
        self,
        *,
        client: AshbyPublicJobClient | None = None,
        parser: AshbyJobParser | None = None,
        min_confidence: float | None = None,
        min_gap: float | None = None,
    ) -> None:
        settings = get_settings()
        self.client = client or AshbyPublicJobClient()
        self.parser = parser or AshbyJobParser()
        self.min_confidence = settings.ASHBY_JOB_MATCH_MIN_CONFIDENCE if min_confidence is None else min_confidence
        self.min_gap = settings.ASHBY_JOB_MATCH_MIN_GAP if min_gap is None else min_gap

    async def enrich(
        self,
        detection: JobSourceDetectionResult,
        *,
        job: Job | None = None,
    ) -> JobDetailExtractionResult:
        if detection.source_type != JobSourceType.ASHBY_JOB_BOARD or not detection.board_slug:
            return _empty(detection, "unsupported_job_source")
        logger.info("Ashby enrichment started", extra={"board_slug": detection.board_slug})
        board = await self.client.list_published_jobs(detection.board_slug)
        if board.reason:
            return _empty(
                detection,
                _normalize_client_reason(board.reason),
                evidence={
                    "board_slug": detection.board_slug,
                    "api_status": board.status_code,
                    "response_size": board.response_size,
                },
            )
        listed = [posting for posting in board.jobs if posting.is_listed is not False and posting.title]
        if not listed:
            return _empty(
                detection,
                "ashby_no_published_jobs",
                evidence=_provider_evidence(detection, board.jobs, listed, board.status_code, board.response_size),
            )

        match = (
            _match_exact(detection, listed)
            if detection.job_identifier
            else _match_board_level(
                job,
                listed,
                min_confidence=self.min_confidence,
                min_gap=self.min_gap,
            )
        )
        evidence = {
            **_provider_evidence(detection, board.jobs, listed, board.status_code, board.response_size),
            "match_strategy": match.reason,
            "match_confidence": round(match.confidence, 3),
            "candidate_scores": [
                {"posting_id": item.posting_id, "title": item.title, "score": round(item.score, 3), "reasons": item.reasons[:8]}
                for item in match.candidate_scores[:10]
            ],
            "selected_posting_id": match.selected_posting.id if match.selected_posting else None,
            "second_best_score": round(match.candidate_scores[1].score, 3) if len(match.candidate_scores) > 1 else None,
            "score_gap": round(match.candidate_scores[0].score - match.candidate_scores[1].score, 3) if len(match.candidate_scores) > 1 else None,
        }
        if match.selected_posting is None:
            logger.info(
                "Ashby posting unresolved",
                extra={"reason": match.reason, "board_slug": detection.board_slug},
            )
            return _empty(detection, match.reason, evidence=evidence, warnings=match.warnings)

        parsed = self.parser.parse_posting(match.selected_posting, board_slug=detection.board_slug)
        parsed_evidence = {
            **parsed.evidence,
            **evidence,
            "parser_warnings": parsed.warnings[:20],
        }
        logger.info(
            "Ashby posting selected",
            extra={
                "board_slug": detection.board_slug,
                "posting_id": match.selected_posting.id,
                "reason": match.reason,
            },
        )
        return JobDetailExtractionResult(
            **{
                **parsed.__dict__,
                "provider": self.provider_name,
                "source_url": parsed.source_url,
                "canonical_url": parsed.canonical_url,
                "evidence": parsed_evidence,
                "reason": match.reason,
                "warnings": [*parsed.warnings, *match.warnings],
            }
        )


def _match_exact(
    detection: JobSourceDetectionResult,
    postings: list[AshbyPublicJobPosting],
) -> AshbyPostingMatchResult:
    stored = detection.job_identifier
    matches = []
    for posting in postings:
        identifiers = {
            posting.id,
            parse_ashby_posting_identifier(posting.job_url),
            parse_ashby_posting_identifier(posting.apply_url),
        }
        canonical = normalize_job_url(posting.job_url).canonical_url if posting.job_url else None
        if stored in identifiers or (canonical and canonical == detection.canonical_url):
            matches.append(posting)
    if len(matches) == 1:
        logger.info("Exact Ashby posting matched", extra={"posting_id": matches[0].id})
        return AshbyPostingMatchResult(matches[0], 1.0, "exact_ashby_posting_match")
    if len(matches) > 1:
        return AshbyPostingMatchResult(None, 0, "ambiguous_ashby_posting_match", ambiguity=True)
    return AshbyPostingMatchResult(None, 0, "ashby_posting_not_found")


def _match_board_level(
    job: Job | None,
    postings: list[AshbyPublicJobPosting],
    *,
    min_confidence: float,
    min_gap: float,
) -> AshbyPostingMatchResult:
    if len(postings) == 1:
        return AshbyPostingMatchResult(
            postings[0],
            1.0,
            "unique_ashby_board_match",
            [_score_candidate(job, postings[0])],
        )
    if job is None:
        return AshbyPostingMatchResult(None, 0, "ashby_board_requires_job_matching")
    if _generic_title(job.title):
        scores = sorted((_score_candidate(job, posting) for posting in postings), key=lambda item: item.score, reverse=True)
        return AshbyPostingMatchResult(None, scores[0].score if scores else 0, "ambiguous_ashby_job_matches", scores, ambiguity=True)
    scores = sorted((_score_candidate(job, posting) for posting in postings), key=lambda item: item.score, reverse=True)
    if not scores:
        return AshbyPostingMatchResult(None, 0, "no_matching_ashby_job")
    best = scores[0]
    second = scores[1].score if len(scores) > 1 else 0
    gap = best.score - second
    if best.score >= min_confidence and gap >= min_gap and "specific_title_signal" in best.reasons:
        selected = next(posting for posting in postings if posting.id == best.posting_id or posting.title == best.title)
        return AshbyPostingMatchResult(selected, best.score, "unique_ashby_board_match", scores)
    reason = "ambiguous_ashby_job_matches" if len(scores) > 1 and gap < min_gap else "no_matching_ashby_job"
    return AshbyPostingMatchResult(None, best.score, reason, scores, ambiguity=reason.startswith("ambiguous"))


def _score_candidate(job: Job | None, posting: AshbyPublicJobPosting) -> AshbyPostingCandidateScore:
    if job is None:
        return AshbyPostingCandidateScore(posting.id, posting.title, 0, [])
    reasons: list[str] = []
    score = 0.0
    job_title = normalize_title(job.title or "")
    posting_title = normalize_title(posting.title or "")
    if job_title and posting_title and job_title == posting_title:
        score += 0.72
        reasons.extend(["exact_normalized_title_match", "specific_title_signal"])
    overlap = _token_overlap(job.title, posting.title)
    if overlap >= 0.75 and not _generic_title(job.title):
        score += 0.25
        reasons.extend(["strong_title_token_overlap", "specific_title_signal"])
    elif overlap >= 0.45:
        score += 0.1
        reasons.append("moderate_title_token_overlap")

    evidence_text = " ".join(
        str(item or "")
        for item in (
            getattr(job, "description", None),
            getattr(job, "job_url", None),
            getattr(job, "source_platform", None),
        )
    )
    posting_identifier = parse_ashby_posting_identifier(posting.job_url) or posting.id
    if posting_identifier and posting_identifier in evidence_text:
        score += 0.65
        reasons.extend(["posting_identifier_in_evidence", "specific_title_signal"])
    if posting.title and posting.title.lower() in evidence_text.lower():
        score += 0.45
        reasons.extend(["title_in_evidence", "specific_title_signal"])
    if job.role_category:
        posting_category = classify_role_category(posting.title, _department_team(posting), _description_hint(posting))
        if str(job.role_category) == posting_category:
            score += 0.12
            reasons.append("matching_role_category")
        elif posting_category != "other":
            score -= 0.15
            reasons.append("conflicting_role_category")
    if job.location and posting.location and _token_overlap(job.location, posting.location) >= 0.5:
        score += 0.08
        reasons.append("matching_location")
    if _seniority_conflict(job.title, posting.title):
        score -= 0.12
        reasons.append("conflicting_seniority")
    score = max(0, min(1.0, score))
    logger.info("Ashby board candidate scored", extra={"posting_id": posting.id, "score": round(score, 3)})
    return AshbyPostingCandidateScore(posting.id, posting.title, score, reasons)


def _provider_evidence(
    detection: JobSourceDetectionResult,
    jobs: list[AshbyPublicJobPosting],
    listed: list[AshbyPublicJobPosting],
    status_code: int | None,
    response_size: int | None,
) -> dict[str, Any]:
    return {
        "board_slug": detection.board_slug,
        "stored_job_identifier": detection.job_identifier,
        "posting_count": len(jobs),
        "listed_posting_count": len(listed),
        "skipped_posting_count": len(jobs) - len(listed),
        "api_status": status_code,
        "response_size": response_size,
    }


def _empty(
    detection: JobSourceDetectionResult,
    reason: str,
    *,
    evidence: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> JobDetailExtractionResult:
    return JobDetailExtractionResult(
        success=False,
        provider=PROVIDER_NAME,
        source_url=detection.canonical_url or detection.original_url or "",
        canonical_url=detection.canonical_url or "",
        reason=reason,
        evidence=evidence or {},
        warnings=warnings or [],
    )


def _normalize_client_reason(reason: str) -> str:
    if reason == "ashby_unexpected_content_type":
        return "ashby_invalid_response"
    if reason == "ashby_invalid_board_slug":
        return "ashby_invalid_response"
    return reason


def _generic_title(value: str | None) -> bool:
    normalized = normalize_title(value or "")
    return normalized in GENERIC_BOARD_TITLES or is_generic_job_title(value)


def _tokens(value: str | None) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9+#.]+", (value or "").lower()) if token not in WEAK_TOKENS}


def _token_overlap(left: str | None, right: str | None) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0
    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


def _department_team(posting: AshbyPublicJobPosting) -> str | None:
    return " ".join(item for item in (posting.department, posting.team) if item) or None


def _description_hint(posting: AshbyPublicJobPosting) -> str | None:
    return posting.description_plain or None


def _seniority_conflict(left: str | None, right: str | None) -> bool:
    def level(value: str | None) -> str | None:
        text = (value or "").lower()
        if "staff" in text or "principal" in text:
            return "staff"
        if "senior" in text:
            return "senior"
        if "junior" in text or "entry" in text:
            return "junior"
        return None

    left_level = level(left)
    right_level = level(right)
    return bool(left_level and right_level and left_level != right_level)

