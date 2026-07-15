import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup

from app.discovery.sources.remotive.constants import REMOTIVE_ALLOWED_HOST
from app.discovery.sources.remotive.models import RemotiveJobPayload
from app.utils.text import normalize_text, normalize_title, repair_mojibake


@dataclass(frozen=True)
class ParsedRemotiveJob:
    source_item_id: str
    title: str
    normalized_title: str
    company_name: str | None
    description: str | None
    excerpt: str | None
    source_url: str | None
    category: str | None
    role_category: str | None
    role_match_type: str | None
    remote_eligibility: str | None
    remote_type: str | None
    seniority: str | None
    employment_type: str | None
    experience_min: int | None
    experience_max: int | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    salary_text: str | None
    published_at: datetime | None
    location: str | None
    accepted: bool = False
    rejection_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class RemotiveJobParser:
    def parse(self, payload: RemotiveJobPayload) -> ParsedRemotiveJob:
        title = normalize_text(payload.title) or ""
        company_name = normalize_text(payload.company_name)
        description = clean_description(payload.description_html)
        source_url = canonical_remotive_url(payload.url)
        source_item_id = payload.source_id or source_url or _fallback_identity(payload)
        salary_min, salary_max, currency, salary_text = parse_salary(payload.salary_text)
        employment_type = normalize_employment_type(payload.job_type)
        metadata = {
            "category": normalize_text(payload.category),
            "job_type": normalize_text(payload.job_type),
            "candidate_required_location": normalize_text(payload.candidate_required_location),
            "salary_text": salary_text,
            "published_at": payload.publication_date.isoformat() if payload.publication_date else None,
        }
        return ParsedRemotiveJob(
            source_item_id=str(source_item_id),
            title=title,
            normalized_title=normalize_title(title) or title.lower(),
            company_name=company_name,
            description=description,
            excerpt=(description or "")[:500] or None,
            source_url=source_url,
            category=normalize_text(payload.category),
            role_category=None,
            role_match_type=None,
            remote_eligibility=None,
            remote_type=None,
            seniority=None,
            employment_type=employment_type,
            experience_min=None,
            experience_max=None,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=currency,
            salary_text=salary_text or normalize_text(payload.salary_text),
            published_at=payload.publication_date,
            location=normalize_text(payload.candidate_required_location) or "Remote",
            metadata={key: value for key, value in metadata.items() if value is not None},
            warnings=[f"publication_date:{payload.publication_date_parse_error}"] if payload.publication_date_parse_error else [],
        )


def clean_description(value: str | None, *, limit: int = 12_000) -> str | None:
    if not value:
        return None
    soup = BeautifulSoup(repair_mojibake(value) or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "form", "iframe", "img"]):
        tag.decompose()
    lines = []
    seen = set()
    for raw in soup.get_text("\n").splitlines():
        line = normalize_text(raw)
        if not line:
            continue
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return "\n".join(lines)[:limit].rstrip() or None


def canonical_remotive_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.hostname != REMOTIVE_ALLOWED_HOST or parsed.username or parsed.password:
        return None
    if "/remote-jobs/" not in parsed.path:
        return None
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunparse(("https", REMOTIVE_ALLOWED_HOST, parsed.path.rstrip("/"), "", urlencode(kept), ""))


def normalize_employment_type(value: str | None) -> str | None:
    text = (value or "").lower().replace("-", " ").replace("_", " ")
    if "full" in text:
        return "full_time"
    if "part" in text:
        return "part_time"
    if "contract" in text or "freelance" in text:
        return "contract"
    if "intern" in text:
        return "internship"
    if "temporary" in text:
        return "temporary"
    return "other" if text.strip() else None


def parse_salary(value: str | None) -> tuple[int | None, int | None, str | None, str | None]:
    text = normalize_text(value) or ""
    if not text:
        return None, None, None, None
    annual = bool(re.search(r"\b(annual|annually|yearly|per year|/year|/yr)\b", text, re.I))
    match = re.search(r"([$€£]|USD|EUR|GBP)\s?(\d[\d,]*(?:k)?)\s*(?:-|–|to)\s*([$€£]|USD|EUR|GBP)?\s?(\d[\d,]*(?:k)?)", text, re.I)
    if not match:
        return None, None, _currency_from_text(text), text
    currency = _currency(match.group(1) or match.group(3))
    if not annual:
        return None, None, currency, match.group(0)
    return _money(match.group(2)), _money(match.group(4)), currency, match.group(0)


def _money(value: str) -> int:
    text = value.lower().replace(",", "")
    return int(float(text.rstrip("k")) * (1000 if text.endswith("k") else 1))


def _currency(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.upper()
    return {"$": "USD", "€": "EUR", "£": "GBP"}.get(normalized, normalized)


def _currency_from_text(text: str) -> str | None:
    if "$" in text or re.search(r"\bUSD\b", text, re.I):
        return "USD"
    if "€" in text or re.search(r"\bEUR\b", text, re.I):
        return "EUR"
    if "£" in text or re.search(r"\bGBP\b", text, re.I):
        return "GBP"
    return None


def _fallback_identity(payload: RemotiveJobPayload) -> str:
    return "|".join(part for part in (payload.company_name, payload.title, payload.url) if part)
