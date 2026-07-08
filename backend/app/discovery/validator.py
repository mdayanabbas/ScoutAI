import re
from dataclasses import dataclass

from app.schemas.discovery import NormalizedStartupCandidate, RawStartupCandidate

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)([a-z0-9-]{1,63}\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CandidateValidationResult:
    valid: bool
    reason: str | None = None


def _looks_like_job_post(candidate: RawStartupCandidate) -> bool:
    haystack = " ".join(
        value or ""
        for value in [candidate.name, candidate.description, candidate.website_url]
    ).lower()
    job_markers = [" job ", " jobs ", " hiring ", " opening ", " role ", " careers"]
    company_markers = [" startup", " company", " platform", " builds", " building"]
    return any(marker in f" {haystack} " for marker in job_markers) and not any(
        marker in haystack for marker in company_markers
    )


def validate_candidate(
    raw_candidate: RawStartupCandidate,
    normalized_candidate: NormalizedStartupCandidate,
) -> CandidateValidationResult:
    if not normalized_candidate.name.strip():
        return CandidateValidationResult(False, "missing_company_name")
    if not normalized_candidate.source_identifier.strip():
        return CandidateValidationResult(False, "missing_source_identifier")
    if raw_candidate.website_url and not normalized_candidate.normalized_domain:
        return CandidateValidationResult(False, "invalid_website_url")
    if normalized_candidate.normalized_domain and not DOMAIN_RE.match(
        normalized_candidate.normalized_domain
    ):
        return CandidateValidationResult(False, "invalid_normalized_domain")
    if _looks_like_job_post(raw_candidate):
        return CandidateValidationResult(False, "job_post_without_company_identity")
    return CandidateValidationResult(True)
