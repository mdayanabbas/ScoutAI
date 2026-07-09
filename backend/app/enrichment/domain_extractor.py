import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

from app.models.discovery_candidate import DiscoveryCandidate
from app.utils.urls import normalize_domain, normalize_url

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "yahoo.com",
    "proton.me",
    "protonmail.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "hey.com",
}

SHARED_PLATFORM_DOMAINS = {
    "news.ycombinator.com",
    "ycombinator.com",
    "github.com",
    "github.io",
    "ashbyhq.com",
    "jobs.ashbyhq.com",
    "greenhouse.io",
    "boards.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "linkedin.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "youtu.be",
    "producthunt.com",
    "reddit.com",
    "medium.com",
    "substack.com",
    "notion.site",
    "notion.so",
}

URL_RE = re.compile(r"https?://[^\s<>\[\]{}\"']+|(?:www\.)[^\s<>\[\]{}\"']+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b", re.IGNORECASE)
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$",
    re.IGNORECASE,
)
INVALID_HOST_CHARS_RE = re.compile(r"[&;/\\\s<>'\"%]")


@dataclass(frozen=True)
class DomainProposal:
    value: str
    domain: str
    source: str
    resolver: str
    reason: str


def extract_urls_from_text(text: str | None) -> list[str]:
    if not text:
        return []
    cleaned = clean_enrichment_text(text)
    return [_trim_url(match.group(0)) for match in URL_RE.finditer(cleaned)]


def extract_email_domains_from_text(text: str | None) -> list[str]:
    if not text:
        return []
    cleaned = clean_enrichment_text(text)
    return [match.group(1).lower() for match in EMAIL_RE.finditer(cleaned)]


def clean_enrichment_text(text: str | None) -> str:
    if not text:
        return ""
    decoded = unescape(text)
    decoded = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", decoded)
    decoded = re.sub(r"<[^>]+>", " ", decoded)
    decoded = re.sub(r"[\u00a0\u2007\u202f\t\r\f\v]+", " ", decoded)
    decoded = re.sub(r"\s+", " ", decoded)
    return decoded.strip()


def collect_candidate_domain_proposals(
    candidate: DiscoveryCandidate,
) -> list[DomainProposal]:
    proposals: list[DomainProposal] = []

    def add(value: str | None, source: str, resolver: str, reason: str) -> None:
        normalized = normalize_domain_proposal(value)
        if not normalized:
            return
        proposals.append(
            DomainProposal(
                value=value or normalized,
                domain=normalized,
                source=source,
                resolver=resolver,
                reason=reason,
            )
        )

    add(candidate.raw_website_url, "raw_website_url", "existing_url", "existing candidate URL")
    add(
        candidate.normalized_website_url,
        "normalized_website_url",
        "existing_url",
        "existing normalized candidate URL",
    )

    text_sources = [
        ("raw_description", candidate.raw_description),
        ("normalized_description", candidate.normalized_description),
        ("raw_payload.text", (candidate.raw_payload or {}).get("text")),
        ("raw_payload.url", (candidate.raw_payload or {}).get("url")),
    ]
    for source, text in text_sources:
        for url in extract_urls_from_text(text):
            add(url, source, "description_url", "URL in candidate text")
        for domain in extract_email_domains_from_text(text):
            add(domain, source, "business_email_domain", "business email domain")

    for evidence in candidate.evidence:
        for source, text in [
            ("evidence.title", evidence.title),
            ("evidence.excerpt", evidence.excerpt),
            ("evidence.source_url", evidence.source_url),
        ]:
            for url in extract_urls_from_text(text):
                add(url, source, "evidence_url", "URL in discovery evidence")
            for domain in extract_email_domains_from_text(text):
                add(domain, source, "business_email_domain", "business email domain")

    deduped: dict[str, DomainProposal] = {}
    for proposal in proposals:
        if is_allowed_company_domain(proposal.domain):
            deduped.setdefault(proposal.domain, proposal)
    return list(deduped.values())


def normalize_domain_proposal(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _trim_url(clean_enrichment_text(value))
    if not cleaned:
        return None
    parsed = urlparse(cleaned if "://" in cleaned else f"https://{cleaned}")
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return None
    if parsed.username or parsed.password:
        return None
    raw_host = parsed.netloc or parsed.path.split("/", 1)[0]
    if "@" in raw_host:
        return None
    normalized = normalize_domain(raw_host)
    normalized = normalized.lower().rstrip(".")
    if not is_valid_hostname(normalized):
        return None
    return normalized or None


def is_allowed_company_domain(domain: str) -> bool:
    return (
        bool(domain)
        and "." in domain
        and is_valid_hostname(domain)
        and not domain.startswith("localhost")
        and not is_free_email_domain(domain)
        and not is_platform_or_shared_domain(domain)
    )


def is_free_email_domain(domain: str) -> bool:
    return domain.lower() in FREE_EMAIL_DOMAINS


def is_platform_or_shared_domain(domain: str) -> bool:
    value = domain.lower()
    if value in SHARED_PLATFORM_DOMAINS:
        return True
    return any(value.endswith(f".{blocked}") for blocked in SHARED_PLATFORM_DOMAINS)


def is_valid_hostname(domain: str | None) -> bool:
    if not domain:
        return False
    value = domain.strip().lower().rstrip(".")
    if (
        not value
        or ".." in value
        or INVALID_HOST_CHARS_RE.search(value)
        or "&#" in value
        or "&" in value
    ):
        return False
    return bool(DOMAIN_RE.match(value))


def _trim_url(value: str) -> str:
    trimmed = value.strip()
    while trimmed and trimmed[-1] in ".,;:)]}'\"":
        trimmed = trimmed[:-1]
    return trimmed
