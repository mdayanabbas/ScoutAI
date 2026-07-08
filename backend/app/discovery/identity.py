import re
from typing import Any

from app.discovery.url_classifier import CandidateUrlType
from app.schemas.discovery import NormalizedStartupCandidate, RawStartupCandidate

SUPPORTED_COMPANY_SLUG_PLATFORMS = {"ashby", "greenhouse", "lever", "ycombinator"}

JOB_MARKERS = (
    " job ",
    " jobs ",
    " hiring ",
    " is hiring ",
    " looking for ",
    " engineer ",
    " careers",
    " role ",
)

GENERIC_COMPANY_NAMES = {
    "stealth",
    "stealth startup",
    "stealth company",
    "startup",
    "company",
    "hiring",
    "backend engineer",
    "frontend engineer",
    "software engineer",
    "engineer",
}


def get_candidate_url_classification(candidate: RawStartupCandidate) -> dict[str, Any]:
    payload = candidate.raw_payload or {}
    classification = payload.get("url_classification")
    if isinstance(classification, dict):
        return classification
    return {}


def get_hacker_news_feed(candidate: RawStartupCandidate) -> str | None:
    payload = candidate.raw_payload or {}
    feed = payload.get("feed")
    return feed if isinstance(feed, str) else None


def candidate_has_job_language(candidate: RawStartupCandidate) -> bool:
    haystack = " ".join(
        value or ""
        for value in [candidate.name, candidate.description, candidate.website_url]
    ).lower()
    padded = f" {haystack} "
    return any(marker in padded for marker in JOB_MARKERS)


def has_reliable_company_identity(
    raw_candidate: RawStartupCandidate,
    normalized_candidate: NormalizedStartupCandidate,
) -> bool:
    classification = get_candidate_url_classification(raw_candidate)
    platform = classification.get("platform")
    company_slug = classification.get("external_company_slug")
    repository = classification.get("external_repository")
    url_type = classification.get("url_type")
    is_first_party = classification.get("is_first_party_company_domain") is True

    if normalized_candidate.normalized_domain and (
        is_first_party or url_type == CandidateUrlType.FIRST_PARTY.value or not platform
    ):
        return True
    if platform in SUPPORTED_COMPANY_SLUG_PLATFORMS and company_slug:
        return True
    if repository:
        return True
    return _has_reliable_name(normalized_candidate.name)


def _has_reliable_name(name: str | None) -> bool:
    if not name:
        return False
    cleaned = re.sub(r"\s+", " ", name).strip().lower()
    if cleaned in GENERIC_COMPANY_NAMES:
        return False
    if cleaned.startswith("stealth "):
        return False
    if len(cleaned.split()) > 8:
        return False
    return True
