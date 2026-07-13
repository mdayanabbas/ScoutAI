import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from app.jobs.enrichment.models import JobDetailExtractionResult, JobFieldValue
from app.jobs.enrichment.parsers.ycombinator_job_parser import (
    MAX_DESCRIPTION_CHARS,
    classify_role_category,
)
from app.jobs.enrichment.providers.ashby_models import AshbyPublicJobPosting
from app.jobs.job_source_detector import normalize_job_url, parse_ashby_job_url
from app.utils.enums import RemoteType
from app.utils.text import repair_mojibake, strip_job_title_action_suffix

PROVIDER = "ashby_public_job_board"
TECH_WORDS = {
    "AI",
    "AWS",
    "Azure",
    "C++",
    "Django",
    "Docker",
    "FastAPI",
    "GCP",
    "Go",
    "GraphQL",
    "Java",
    "JavaScript",
    "Kubernetes",
    "LLM",
    "Node.js",
    "PostgreSQL",
    "Python",
    "React",
    "Redis",
    "Ruby",
    "Rust",
    "SQL",
    "TypeScript",
}


class AshbyJobParser:
    def parse_posting(
        self,
        posting: AshbyPublicJobPosting,
        *,
        board_slug: str,
    ) -> JobDetailExtractionResult:
        canonical_url = _safe_job_url(posting.job_url, board_slug, posting.id)
        source_url = canonical_url or posting.job_url or f"https://jobs.ashbyhq.com/{board_slug}"
        description = _description(posting)
        location_text = _location(posting)
        raw_role = _raw_role(posting)
        role_category = classify_role_category(
            posting.title,
            raw_role,
            description,
        )
        salary_min, salary_max, currency, salary_text = _salary_fields(posting.compensation)
        fields = {
            "title": _field(strip_job_title_action_suffix(posting.title), 1.0, "ashby_api_title"),
            "description": _field(description, 0.95, "ashby_description"),
            "role_category": _field(role_category, 0.95 if role_category != "other" else 0.65, "deterministic_role_classifier"),
            "seniority": _seniority_field(posting.title, description),
            "location": _field(location_text, 0.94, "ashby_location"),
            "remote_type": _remote_type_field(posting),
            "employment_type": _employment_type_field(posting.employment_type),
            "experience_min": _experience_fields(posting.title, description)[0],
            "experience_max": _experience_fields(posting.title, description)[1],
            "salary_min": _field(salary_min, 0.9, "ashby_compensation"),
            "salary_max": _field(salary_max, 0.9, "ashby_compensation"),
            "salary_currency": _field(currency, 0.9, "ashby_compensation"),
            "salary_text": _field(salary_text, 0.9, "ashby_compensation"),
            "equity_mentioned": _equity_field(posting.compensation, description),
            "job_url": _field(canonical_url, 0.98, "ashby_job_url"),
            "apply_url": _field(_safe_apply_url(posting.apply_url), 0.9, "ashby_apply_url"),
            "technologies": _technology_field(description),
            "published_at": _published_at_field(posting.published_at),
            "raw_role": _field(raw_role, 0.85, "ashby_department_team"),
        }
        confidence = {key: round(value.confidence, 3) for key, value in fields.items() if value}
        important_scores = [
            value.confidence for key, value in fields.items() if key in {"title", "description", "role_category", "location", "employment_type"} and value
        ]
        overall = min(1.0, sum(important_scores) / max(3, len(important_scores))) if important_scores else 0
        evidence = {
            "parser": "ashby_job_parser",
            "posting_id": posting.id,
            "posting_raw_index": posting.raw_index,
            "department": posting.department,
            "team": posting.team,
            "workplace_type": posting.workplace_type,
            "is_remote": posting.is_remote,
            "employment_type_raw": posting.employment_type,
            "compensation_text": _bounded(_compensation_text(posting.compensation), 500),
            "overall_confidence": round(overall, 3),
            "extracted_field_names": sorted(confidence),
        }
        success = bool(fields["title"])
        return JobDetailExtractionResult(
            success=success,
            provider=PROVIDER,
            source_url=source_url,
            canonical_url=canonical_url or source_url,
            title=fields["title"],
            description=fields["description"],
            role_category=fields["role_category"],
            seniority=fields["seniority"],
            location=fields["location"],
            remote_type=fields["remote_type"],
            employment_type=fields["employment_type"],
            experience_min=fields["experience_min"],
            experience_max=fields["experience_max"],
            salary_min=fields["salary_min"],
            salary_max=fields["salary_max"],
            salary_currency=fields["salary_currency"],
            salary_text=fields["salary_text"],
            equity_mentioned=fields["equity_mentioned"],
            job_url=fields["job_url"],
            apply_url=fields["apply_url"],
            technologies=fields["technologies"],
            published_at=fields["published_at"],
            raw_role=fields["raw_role"],
            field_confidence=confidence,
            evidence=evidence,
            reason="valid_supported_source" if success else "ashby_job_data_missing",
        )


def parse_ashby_posting_identifier(url: str | None) -> str | None:
    parsed = parse_ashby_job_url(url)
    if parsed and parsed.exact_posting:
        return parsed.job_identifier
    if not url:
        return None
    path_parts = [unquote(part) for part in urlparse(url).path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[-1] != path_parts[0]:
        candidate = path_parts[-1]
        if re.fullmatch(r"[A-Za-z0-9_-]{1,160}", candidate):
            return candidate
    return None


def _field(value: Any, confidence: float, source: str, evidence: dict[str, Any] | None = None) -> JobFieldValue | None:
    if value is None or value == "" or value == []:
        return None
    return JobFieldValue(value, confidence, source, evidence or {})


def _description(posting: AshbyPublicJobPosting) -> str | None:
    if posting.description_plain:
        return _bounded(_clean_description(repair_mojibake(posting.description_plain) or ""), MAX_DESCRIPTION_CHARS)
    if posting.description_html:
        soup = BeautifulSoup(posting.description_html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        return _bounded(_clean_description(repair_mojibake(soup.get_text("\n")) or ""), MAX_DESCRIPTION_CHARS)
    return None


def _location(posting: AshbyPublicJobPosting) -> str | None:
    values = [posting.location, *posting.secondary_locations]
    result = []
    for item in values:
        cleaned = repair_mojibake(item) if item else None
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return " / ".join(result) if result else None


def _remote_type_field(posting: AshbyPublicJobPosting) -> JobFieldValue | None:
    workplace = (posting.workplace_type or "").lower().replace("-", "").replace("_", "")
    if workplace in {"onsite", "on site"}:
        return _field(RemoteType.ONSITE.value, 0.95, "ashby_workplace_type")
    if "hybrid" in workplace:
        return _field(RemoteType.HYBRID.value, 0.95, "ashby_workplace_type")
    if "remote" in workplace:
        return _field(RemoteType.REMOTE_WORLDWIDE.value, 0.95, "ashby_workplace_type")
    if posting.is_remote is True:
        return _field(RemoteType.REMOTE_WORLDWIDE.value, 0.9, "ashby_is_remote")
    if posting.is_remote is False:
        return _field(RemoteType.ONSITE.value, 0.75, "ashby_is_remote")
    return None


def _employment_type_field(value: str | None) -> JobFieldValue | None:
    if not value:
        return None
    lower = value.lower().replace("_", "-")
    if "full" in lower:
        normalized = "full_time"
    elif "part" in lower:
        normalized = "part_time"
    elif "contract" in lower:
        normalized = "contract"
    elif "intern" in lower:
        normalized = "internship"
    elif "temporary" in lower:
        normalized = "temporary"
    else:
        normalized = "other"
    return _field(normalized, 0.95, "ashby_employment_type", {"raw": value})


def _experience_fields(title: str | None, description: str | None) -> tuple[JobFieldValue | None, JobFieldValue | None]:
    text = " ".join(item for item in (title, description) if item)
    match = re.search(r"\b(\d+)\s*(?:-|to|\u2013)\s*(\d+)\s*\+?\s+years?", text, re.IGNORECASE)
    if match:
        return _field(int(match.group(1)), 0.9, "experience_text"), _field(int(match.group(2)), 0.9, "experience_text")
    match = re.search(r"\b(\d+)\s*\+\s+years?", text, re.IGNORECASE)
    if match:
        return _field(int(match.group(1)), 0.9, "experience_text"), None
    return None, None


def _seniority_field(title: str | None, description: str | None) -> JobFieldValue | None:
    text = f"{title or ''} {description or ''}".lower()
    if "staff" in text:
        return _field("staff", 0.9, "title_description")
    if "principal" in text:
        return _field("principal", 0.9, "title_description")
    if "senior" in text or re.search(r"\b5\+\s+years?", text):
        return _field("senior", 0.85, "title_description")
    if "junior" in text or "entry level" in text:
        return _field("entry_level", 0.85, "title_description")
    return None


def _salary_fields(compensation: Any) -> tuple[int | None, int | None, str | None, str | None]:
    text = _compensation_text(compensation)
    if not text:
        return None, None, None, None
    salary_part = _salary_text_from_text(text)
    if not salary_part:
        return None, None, None, _bounded(text, 1000)
    currency = _currency(salary_part)
    numbers = re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([Kk])?", salary_part)
    values = [_salary_number(number, suffix) for number, suffix in numbers[:2]]
    return values[0] if values else None, values[1] if len(values) > 1 else values[0] if values else None, currency, _bounded(text, 1000)


def _compensation_text(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        pieces = []
        for key in ("salary", "baseSalary", "compensationTierSummary", "summary", "description"):
            item = value.get(key)
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                pieces.extend(str(v) for v in item.values() if v is not None)
        if pieces:
            return " ".join(pieces)
    if isinstance(value, list):
        return " ".join(filter(None, (_compensation_text(item) for item in value)))
    return str(value)


def _salary_text_from_text(text: str) -> str | None:
    match = re.search(r"((?:USD|EUR|GBP|\$|\u20ac|\u00a3)\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?\s*(?:-|\u2013|to)\s*(?:USD|EUR|GBP|\$|\u20ac|\u00a3)?\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"((?:USD|EUR|GBP|\$|\u20ac|\u00a3)\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?)", text, re.IGNORECASE)
    return match.group(1) if match else None


def _salary_number(number: str, suffix: str) -> int:
    value = float(number.replace(",", ""))
    if suffix.lower() == "k":
        value *= 1000
    return int(value)


def _currency(text: str) -> str | None:
    if "$" in text or re.search(r"\bUSD\b", text, re.IGNORECASE):
        return "USD"
    if "\u20ac" in text or re.search(r"\bEUR\b", text, re.IGNORECASE):
        return "EUR"
    if "\u00a3" in text or re.search(r"\bGBP\b", text, re.IGNORECASE):
        return "GBP"
    return None


def _equity_field(compensation: Any, description: str | None) -> JobFieldValue | None:
    text = " ".join(item for item in (_compensation_text(compensation), description) if item)
    if re.search(r"\d+(?:\.\d+)?%\s*(?:-|\u2013|to)\s*\d+(?:\.\d+)?%", text):
        return _field(True, 0.95, "equity_text")
    if re.search(r"\bequity\b", text, re.IGNORECASE):
        return _field(True, 0.8, "equity_text")
    return None


def _technology_field(description: str | None) -> JobFieldValue | None:
    if not description:
        return None
    found = [word for word in sorted(TECH_WORDS) if re.search(rf"(?<![\w+#]){re.escape(word)}(?![\w+#])", description, re.IGNORECASE)]
    return _field(found, 0.75, "technology_text") if found else None


def _published_at_field(value: str | None) -> JobFieldValue | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _field(parsed, 0.95, "ashby_published_at")


def _safe_job_url(value: str | None, board_slug: str, posting_id: str | None) -> str | None:
    normalized = normalize_job_url(value)
    if normalized.valid and parse_ashby_job_url(normalized.canonical_url):
        parsed = parse_ashby_job_url(normalized.canonical_url)
        if parsed and parsed.exact_posting:
            return parsed.canonical_url
    if posting_id:
        return f"https://jobs.ashbyhq.com/{board_slug}/{posting_id}"
    return None


def _safe_apply_url(value: str | None) -> str | None:
    normalized = normalize_job_url(value)
    return normalized.canonical_url if normalized.valid else None


def _raw_role(posting: AshbyPublicJobPosting) -> str | None:
    values = [posting.department, posting.team]
    return " / ".join(item for item in values if item) or None


def _clean_description(value: str) -> str:
    lines = []
    seen: set[str] = set()
    for raw in value.splitlines():
        line = re.sub(r"\s+", " ", repair_mojibake(raw) or "").strip()
        if not line:
            continue
        lower = line.lower()
        if lower in seen or lower in {"apply now", "view all jobs"}:
            continue
        seen.add(lower)
        lines.append(line)
    return "\n".join(lines)


def _bounded(value: str | None, maximum: int) -> str | None:
    if not value:
        return None
    return value[:maximum].rstrip()
