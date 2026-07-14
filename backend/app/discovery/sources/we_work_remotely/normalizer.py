import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup

from app.discovery.sources.we_work_remotely.constants import WWR_ALLOWED_HOST
from app.utils.text import normalize_text, normalize_title, repair_mojibake


def clean_html_text(value: str | None, *, limit: int = 12_000) -> str | None:
    if not value:
        return None
    soup = BeautifulSoup(repair_mojibake(value) or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "form", "iframe", "img"]):
        tag.decompose()
    lines: list[str] = []
    seen: set[str] = set()
    for raw in soup.get_text("\n").splitlines():
        line = normalize_text(raw)
        if not line:
            continue
        key = line.casefold()
        if key in seen or "we work remotely" == key:
            continue
        if any(token in key for token in ("apply for this position", "view all jobs", "posted on")):
            continue
        seen.add(key)
        lines.append(line)
    return "\n".join(lines)[:limit].rstrip() or None


def parse_rss_datetime(value: str | None) -> tuple[datetime | None, str | None]:
    if not value:
        return None, None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None, "invalid_publication_date"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc), None


def canonical_wwr_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.hostname != WWR_ALLOWED_HOST or parsed.username or parsed.password:
        return None
    if "/remote-jobs/" not in parsed.path and "/listings/" not in parsed.path:
        return None
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunparse(("https", WWR_ALLOWED_HOST, parsed.path.rstrip("/"), "", urlencode(kept), ""))


def parse_title_parts(title: str | None, text: str | None = None) -> tuple[str | None, str | None]:
    value = normalize_text(title)
    if not value:
        return None, None
    for separator in (" — ", " – ", ": "):
        if separator in value:
            company, role = value.split(separator, 1)
            return _clean_company(company), normalize_text(role)
    hyphen = re.match(r"^(.{2,80})\s+-\s+([A-Z][^\n]{2,120})$", value)
    if hyphen and not re.search(r"\b(?:Forward|Full|AI|ML)-", value):
        return _clean_company(hyphen.group(1)), normalize_text(hyphen.group(2))
    at_match = re.match(r"^(.{2,120})\s+at\s+(.{2,80})$", value, re.I)
    if at_match:
        return _clean_company(at_match.group(2)), normalize_text(at_match.group(1))
    company = _company_from_text(text)
    return company, value


def normalize_employment_type(value: str | None) -> str | None:
    text = (value or "").lower().replace("-", " ")
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
    return None


def parse_salary(text: str | None) -> tuple[int | None, int | None, str | None, str | None]:
    value = normalize_text(text) or ""
    match = re.search(r"([$€£])\s?(\d[\d,]*(?:k)?)\s*(?:-|–|to)\s*[$€£]?\s?(\d[\d,]*(?:k)?)\s*(USD|EUR|GBP)?", value, re.I)
    if not match:
        return None, None, None, None
    if re.search(r"\b(hour|hourly|day|daily|week|weekly|month|monthly)\b", value, re.I):
        return None, None, _currency(match.group(1), match.group(4)), match.group(0)
    return _money(match.group(2)), _money(match.group(3)), _currency(match.group(1), match.group(4)), match.group(0)


def normalized_identity(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (normalize_title(value) or "unknown")).strip("-") or "unknown"


def _clean_company(value: str | None) -> str | None:
    text = normalize_text(value)
    if not text or text.lower() == "unknown":
        return None
    return text


def _company_from_text(text: str | None) -> str | None:
    value = text or ""
    for pattern in (r"\bCompany\s*[:\-]\s*([^\n]{2,80})", r"\bOrganization\s*[:\-]\s*([^\n]{2,80})"):
        match = re.search(pattern, value, re.I)
        if match:
            return _clean_company(match.group(1))
    return None


def _money(value: str) -> int:
    text = value.lower().replace(",", "")
    multiplier = 1000 if text.endswith("k") else 1
    return int(float(text.rstrip("k")) * multiplier)


def _currency(symbol: str, explicit: str | None) -> str:
    if explicit:
        return explicit.upper()
    return {"$": "USD", "€": "EUR", "£": "GBP"}.get(symbol, "USD")
