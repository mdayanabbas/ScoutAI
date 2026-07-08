import re

from app.schemas.discovery import NormalizedStartupCandidate, RawStartupCandidate
from app.utils.urls import normalize_domain, normalize_url


class CandidateNormalizationError(ValueError):
    pass


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def normalize_candidate(candidate: RawStartupCandidate) -> NormalizedStartupCandidate:
    name = _clean_text(candidate.name)
    if not name:
        raise CandidateNormalizationError("missing_company_name")

    website_url = None
    normalized_domain = None
    if candidate.website_url:
        website_url = normalize_url(candidate.website_url)
        normalized_domain = normalize_domain(website_url) or None

    return NormalizedStartupCandidate(
        source_identifier=_clean_text(candidate.source_identifier) or "",
        name=name,
        website_url=website_url,
        normalized_domain=normalized_domain,
        description=_clean_text(candidate.description),
        country=_clean_text(candidate.country),
        evidence=candidate.evidence,
        raw_payload=candidate.raw_payload,
    )
