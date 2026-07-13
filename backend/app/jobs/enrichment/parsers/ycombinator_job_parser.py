import json
import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from app.jobs.enrichment.models import JobDetailExtractionResult, JobFieldValue
from app.jobs.job_source_detector import normalize_job_url, parse_yc_job_url
from app.utils.enums import RemoteType, RoleCategory
from app.utils.text import (
    dedupe_meaningful_entries,
    focused_authorization_fields,
    repair_mojibake,
    split_structured_skill_text,
    strip_job_title_action_suffix,
)

logger = logging.getLogger(__name__)

PROVIDER = "ycombinator_job_page"
MAX_DESCRIPTION_CHARS = 12_000
GENERIC_TITLES = {
    "open roles",
    "hiring",
    "is hiring",
    "largest government contract",
    "gtm team",
    "software roles",
    "engineering roles",
    "careers",
    "jobs",
    "join our team",
    "current openings",
    "open positions",
}
CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP"}
SENSITIVE_QUERY_RE = re.compile(r"(token|session|continue|auth|code|state)", re.IGNORECASE)


class YCombinatorJobParser:
    def parse(
        self,
        html: str,
        *,
        source_url: str,
        canonical_url: str,
    ) -> JobDetailExtractionResult:
        if not html or not html.strip():
            return _empty_result(source_url, canonical_url, "yc_job_invalid_html")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            if tag.name == "script" and _script_might_contain_data(tag):
                continue
            tag.decompose()

        json_ld = _jobposting_json_ld(html)
        labels = _labelled_fields(soup)
        text = _clean_text(soup.get_text("\n"))
        warnings: list[str] = []
        evidence: dict[str, Any] = {
            "parser": "ycombinator_job_parser",
            "detected_labels": sorted(labels.keys()),
            "strategy": "visible_html",
        }

        title = _title_field(json_ld, soup, canonical_url)
        if json_ld:
            evidence["strategy"] = "json_ld"
        description = _description_field(json_ld, soup, text)
        location = _location_field(json_ld, labels)
        employment_type = _employment_type_field(json_ld, labels)
        experience_min, experience_max, seniority = _experience_fields(labels, text)
        salary_min, salary_max, salary_currency, salary_text = _salary_fields(json_ld, labels, text, warnings)
        equity = _equity_field(labels, text)
        visa, work_auth = _visa_fields(labels, text)
        required_skills, technologies = _skills_fields(json_ld, labels)
        preferred_skills = _preferred_skills_field(text)
        published_at = _published_at_field(json_ld)
        apply_url = _apply_url_field(json_ld, soup, canonical_url)
        job_url = _field(parse_yc_job_url(canonical_url).canonical_url if parse_yc_job_url(canonical_url) else normalize_job_url(canonical_url).canonical_url, 0.98, "canonical_yc_job")
        raw_role = _raw_role_field(labels)
        role_category = _role_category_field(title, raw_role, description)
        remote_type = _remote_type_field(location, labels)

        fields = {
            "title": title,
            "description": description,
            "role_category": role_category,
            "seniority": seniority,
            "location": location,
            "remote_type": remote_type,
            "employment_type": employment_type,
            "experience_min": experience_min,
            "experience_max": experience_max,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "salary_text": salary_text,
            "equity_mentioned": equity,
            "apply_url": apply_url,
            "job_url": job_url,
            "visa_sponsorship": visa,
            "work_authorization": work_auth,
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "technologies": technologies,
            "published_at": published_at,
            "raw_role": raw_role,
        }
        confidence = {
            key: round(value.confidence, 3)
            for key, value in fields.items()
            if value is not None
        }
        important = [title, description, role_category, employment_type, location]
        important_scores = [item.confidence for item in important if item is not None]
        overall = min(1.0, sum(important_scores) / max(3, len(important_scores))) if important_scores else 0
        evidence["overall_confidence"] = round(overall, 3)
        evidence["extracted_field_names"] = sorted(confidence)
        if not title or title.confidence < 0.75:
            reason = "yc_job_data_missing"
            success = False
        else:
            reason = "valid_supported_source"
            success = True
        logger.info(
            "Parser strategy selected",
            extra={"strategy": evidence["strategy"], "success": success, "reason": reason},
        )
        return JobDetailExtractionResult(
            success=success,
            provider=PROVIDER,
            source_url=source_url,
            canonical_url=canonical_url,
            title=title,
            description=description,
            role_category=role_category,
            seniority=seniority,
            location=location,
            remote_type=remote_type,
            employment_type=employment_type,
            experience_min=experience_min,
            experience_max=experience_max,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            salary_text=salary_text,
            equity_mentioned=equity,
            apply_url=apply_url,
            job_url=job_url,
            visa_sponsorship=visa,
            work_authorization=work_auth,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            technologies=technologies,
            published_at=published_at,
            raw_role=raw_role,
            field_confidence=confidence,
            evidence=evidence,
            reason=reason,
            warnings=warnings,
        )


def classify_role_category(title: str | None, role: str | None = None, description: str | None = None) -> str:
    value = " ".join(item for item in (title, role, description) if item).lower()
    exact = " ".join(item for item in (title, role) if item).lower()
    if "developer advocate" in exact or "devrel" in exact:
        return "developer_advocate"
    if "account executive" in exact or re.search(r"\bsales\b", exact):
        return "sales"
    if "marketing" in exact:
        return "marketing"
    if "product manager" in exact or re.search(r"\bpm\b", exact):
        return "product_manager"
    if "founding product engineer" in exact or "product engineer" in exact:
        return RoleCategory.PRODUCT_ENGINEER.value
    if re.search(r"\bfounding engineer\b", exact):
        return RoleCategory.SOFTWARE_ENGINEER.value
    if "full stack" in exact or "full-stack" in exact:
        return RoleCategory.FULL_STACK_ENGINEER.value
    if "frontend" in exact or "front end" in exact:
        return RoleCategory.FRONTEND_ENGINEER.value
    if "backend" in exact or "back end" in exact:
        return RoleCategory.BACKEND_ENGINEER.value
    if "machine learning" in exact or re.search(r"\bml engineer\b", exact):
        return RoleCategory.ML_ENGINEER.value
    if re.search(r"\b(ai|llm|nlp)\b", exact) and "engineer" in exact:
        return RoleCategory.AI_ENGINEER.value
    if "infrastructure" in exact:
        return "infrastructure_engineer"
    if "devops" in exact or "site reliability" in exact or re.search(r"\bsre\b", exact):
        return RoleCategory.DEVOPS_ENGINEER.value
    if "data engineer" in exact:
        return RoleCategory.DATA_ENGINEER.value
    if "forward deployed" in exact:
        return "forward_deployed_engineer"
    if "operations" in exact:
        return "operations"
    if (
        "software engineer" in exact
        or "software developer" in exact
        or "application developer" in exact
        or "full stack" in exact
        or "full-stack" in exact
        or "web engineer" in exact
        or (("platform engineer" in exact or "engineer" in exact) and "software" in value)
    ):
        return RoleCategory.SOFTWARE_ENGINEER.value
    if "marketing" in value:
        return "marketing"
    if "sales" in value:
        return "sales"
    return RoleCategory.OTHER.value


def is_generic_job_title(value: str | None) -> bool:
    return _normalize_ws(value).lower() in GENERIC_TITLES


def _field(value: Any, confidence: float, source: str, evidence: dict[str, Any] | None = None) -> JobFieldValue | None:
    if value is None or value == "" or value == []:
        return None
    return JobFieldValue(value, confidence, source, evidence or {})


def _empty_result(source_url: str, canonical_url: str, reason: str) -> JobDetailExtractionResult:
    return JobDetailExtractionResult(
        success=False,
        provider=PROVIDER,
        source_url=source_url,
        canonical_url=canonical_url,
        reason=reason,
    )


def _script_might_contain_data(tag) -> bool:
    script_type = (tag.get("type") or "").lower()
    return "json" in script_type


def _jobposting_json_ld(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type=lambda value: value and "ld+json" in value.lower()):
        try:
            payload = json.loads(script.string or script.get_text() or "{}")
        except json.JSONDecodeError:
            continue
        for item in _json_items(payload):
            item_type = item.get("@type")
            if item_type == "JobPosting" or (isinstance(item_type, list) and "JobPosting" in item_type):
                return item
    return {}


def _json_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _labelled_fields(soup: BeautifulSoup) -> dict[str, str]:
    labels: dict[str, str] = {}
    for row in soup.find_all(["li", "div", "p", "span"]):
        text = _normalize_ws(row.get_text(" "))
        if not text or len(text) > 500:
            continue
        match = re.match(r"^(Job type|Type|Role|Experience|Visa|Sponsorship|Work authorization|Skills?|Location|Compensation|Salary)\s*[:\-]\s*(.+)$", text, re.IGNORECASE)
        if match:
            labels[_label_key(match.group(1))] = match.group(2).strip()
            continue
        parts = [part.strip() for part in text.split("\n") if part.strip()]
        if len(parts) == 2 and _label_key(parts[0]):
            labels[_label_key(parts[0])] = parts[1]
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            key = _label_key(dt.get_text(" "))
            if key:
                labels[key] = _normalize_ws(dd.get_text(" "))
    return labels


def _label_key(value: str) -> str:
    normalized = _normalize_ws(value).lower().strip(":")
    mapping = {
        "job type": "job_type",
        "type": "job_type",
        "role": "role",
        "experience": "experience",
        "visa": "visa",
        "sponsorship": "sponsorship",
        "work authorization": "work_authorization",
        "skills": "skills",
        "skill": "skills",
        "location": "location",
        "compensation": "compensation",
        "salary": "compensation",
    }
    return mapping.get(normalized, "")


def _title_field(json_ld: dict[str, Any], soup: BeautifulSoup, canonical_url: str) -> JobFieldValue | None:
    title = strip_job_title_action_suffix(_normalize_ws(json_ld.get("title"))) if json_ld else ""
    if title:
        return _field(title, 1.0, "json_ld", {"source": "JobPosting.title"})
    h1 = soup.find("h1")
    if h1:
        h1_text = strip_job_title_action_suffix(_clean_title(h1.get_text(" ")))
        if h1_text:
            return _field(h1_text, 0.98, "primary_heading")
    og = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "title"})
    if og and og.get("content"):
        text = strip_job_title_action_suffix(_clean_title(str(og["content"])))
        if text:
            return _field(text, 0.9, "open_graph")
    slug_title = _title_from_slug(canonical_url)
    return _field(slug_title, 0.7, "url_slug") if slug_title else None


def _description_field(json_ld: dict[str, Any], soup: BeautifulSoup, visible_text: str) -> JobFieldValue | None:
    description = _html_to_text(json_ld.get("description")) if json_ld.get("description") else ""
    if description:
        return _field(_bounded_description(description), 0.96, "json_ld")
    main = soup.find("main") or soup.body or soup
    for tag in main.find_all(["nav", "footer", "header", "aside"]):
        tag.decompose()
    text = _clean_description(main.get_text("\n"))
    if text:
        return _field(_bounded_description(text), 0.9, "visible_main_content")
    if visible_text:
        return _field(_bounded_description(_clean_description(visible_text)), 0.75, "visible_text")
    return None


def _location_field(json_ld: dict[str, Any], labels: dict[str, str]) -> JobFieldValue | None:
    value = labels.get("location")
    if value:
        return _field(value, 0.95, "labelled_field")
    location = json_ld.get("jobLocation") if json_ld else None
    if isinstance(location, dict):
        address = location.get("address")
        if isinstance(address, dict):
            parts = [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")]
            text = ", ".join(str(part) for part in parts if part)
            return _field(text, 0.93, "json_ld") if text else None
    if isinstance(location, list) and location:
        return _location_field({"jobLocation": location[0]}, labels)
    return None


def _remote_type_field(location: JobFieldValue | None, labels: dict[str, str]) -> JobFieldValue | None:
    text = " ".join(filter(None, [location.value if location else None, labels.get("location")])).lower()
    if not text:
        return None
    if "hybrid" in text:
        return _field(RemoteType.HYBRID.value, 0.9, "location_label")
    if "remote" in text:
        return _field(RemoteType.REMOTE_WORLDWIDE.value, 0.9, "location_label")
    if "on-site" in text or "onsite" in text or "in-person" in text:
        return _field(RemoteType.ONSITE.value, 0.9, "location_label")
    return _field(RemoteType.UNKNOWN.value, 0.65, "location_label")


def _employment_type_field(json_ld: dict[str, Any], labels: dict[str, str]) -> JobFieldValue | None:
    raw = labels.get("job_type") or json_ld.get("employmentType")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    value = _normalize_employment_type(str(raw)) if raw else None
    return _field(value, 0.95, "labelled_field", {"raw": raw}) if value else None


def _experience_fields(labels: dict[str, str], text: str) -> tuple[JobFieldValue | None, JobFieldValue | None, JobFieldValue | None]:
    raw = labels.get("experience")
    if not raw:
        match = re.search(r"\b(\d+)\s*(?:\+|to|-)\s*(\d+)?\s+years?", text, re.IGNORECASE)
        raw = match.group(0) if match else ""
    value = raw.lower()
    if not value:
        return None, None, None
    if "any" in value or "new grads" in value or "new grads ok" in value:
        return (
            _field(0, 0.95, "experience_label", {"raw": raw}),
            None,
            _field("entry_level_or_open", 0.9, "experience_label", {"raw": raw}),
        )
    match = re.search(r"(\d+)\s*\+\s*years?", value)
    if match:
        years = int(match.group(1))
        return (
            _field(years, 0.95, "experience_label", {"raw": raw}),
            None,
            _field("senior" if years >= 6 else "mid_level", 0.85, "experience_label", {"raw": raw}),
        )
    match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*years?", value)
    if match:
        min_years = int(match.group(1))
        max_years = int(match.group(2))
        return (
            _field(min_years, 0.95, "experience_label", {"raw": raw}),
            _field(max_years, 0.95, "experience_label", {"raw": raw}),
            _field("senior" if min_years >= 6 else "mid_level", 0.85, "experience_label", {"raw": raw}),
        )
    return None, None, None


def _salary_fields(
    json_ld: dict[str, Any],
    labels: dict[str, str],
    text: str,
    warnings: list[str],
) -> tuple[JobFieldValue | None, JobFieldValue | None, JobFieldValue | None, JobFieldValue | None]:
    raw = labels.get("compensation") or _salary_text_from_json_ld(json_ld) or _salary_text_from_text(text)
    if not raw:
        return None, None, None, None
    salary_text = _field(raw, 0.95, "compensation_label")
    parsed = _parse_salary(raw)
    if parsed is None:
        warnings.append("salary_text_not_numeric")
        return None, None, None, salary_text
    salary_min, salary_max, currency = parsed
    return (
        _field(salary_min, 0.98, "compensation_label") if salary_min is not None else None,
        _field(salary_max, 0.98, "compensation_label") if salary_max is not None else None,
        _field(currency, 0.98, "compensation_label") if currency else None,
        salary_text,
    )


def _equity_field(labels: dict[str, str], text: str) -> JobFieldValue | None:
    value = " ".join(filter(None, [labels.get("compensation"), text[:2000]]))
    if re.search(r"\d+(?:\.\d+)?%\s*(?:-|–|to)\s*\d+(?:\.\d+)?%", value):
        return _field(True, 0.95, "equity_text", {"text": "percentage_range"})
    if re.search(r"\bmeaningful equity\b|\bequity included\b", value, re.IGNORECASE):
        return _field(True, 0.85, "equity_text")
    if re.search(r"\bno equity\b", value, re.IGNORECASE):
        return _field(False, 0.9, "equity_text")
    return None


def _visa_fields(labels: dict[str, str], text: str) -> tuple[JobFieldValue | None, JobFieldValue | None]:
    visa, focused = focused_authorization_fields(labels, text)
    return (
        _field(visa, 0.9, "authorization_evidence") if visa else None,
        _field(focused, 0.85, "authorization_evidence", {"source": "focused_authorization"}) if focused else None,
    )


def _skills_fields(json_ld: dict[str, Any], labels: dict[str, str]) -> tuple[JobFieldValue | None, JobFieldValue | None]:
    skills_raw = labels.get("skills") or json_ld.get("skills")
    cleaned = _dedupe_list(split_structured_skill_text(skills_raw))
    field = _field(cleaned, 0.95, "skills_label") if cleaned else None
    return field, field
    if isinstance(skills_raw, list):
        skills = [str(item) for item in skills_raw]
    else:
        skills = re.split(r"[,;•|]", str(skills_raw or ""))
    cleaned = _dedupe_list(skills)
    field = _field(cleaned, 0.95, "skills_label") if cleaned else None
    return field, field


def _preferred_skills_field(text: str) -> JobFieldValue | None:
    match = re.search(r"(?is)(Nice to have|Preferred qualifications?)\s*[:\n]\s*(.+?)(?:\n[A-Z][^\n]{1,60}\n|$)", text)
    if not match:
        return None
    skills = _dedupe_list(split_structured_skill_text(match.group(2)))
    return _field(skills[:20], 0.75, "preferred_section") if skills else None
    skills = _dedupe_list(re.split(r"[,;\n•|-]", match.group(2)))
    return _field(skills[:20], 0.75, "preferred_section") if skills else None


def _published_at_field(json_ld: dict[str, Any]) -> JobFieldValue | None:
    value = json_ld.get("datePosted") if json_ld else None
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return _field(parsed, 0.98, "json_ld")


def _apply_url_field(json_ld: dict[str, Any], soup: BeautifulSoup, canonical_url: str) -> JobFieldValue | None:
    raw = json_ld.get("url") or json_ld.get("applicationContact") if json_ld else None
    if isinstance(raw, dict):
        raw = raw.get("url")
    if not raw:
        for link in soup.find_all("a", href=True):
            text = _normalize_ws(link.get_text(" ")).lower()
            if "apply" in text:
                raw = link["href"]
                break
    normalized = _safe_apply_url(str(raw)) if raw else None
    if normalized:
        return _field(normalized, 0.9, "apply_link")
    return _field(canonical_url, 0.75, "canonical_yc_job")


def _raw_role_field(labels: dict[str, str]) -> JobFieldValue | None:
    return _field(labels.get("role"), 0.9, "labelled_field") if labels.get("role") else None


def _role_category_field(
    title: JobFieldValue | None,
    raw_role: JobFieldValue | None,
    description: JobFieldValue | None,
) -> JobFieldValue | None:
    category = classify_role_category(
        title.value if title else None,
        raw_role.value if raw_role else None,
        description.value if description else None,
    )
    confidence = 0.95 if category != RoleCategory.OTHER.value else 0.65
    return _field(category, confidence, "deterministic_role_classifier")


def _salary_text_from_json_ld(json_ld: dict[str, Any]) -> str | None:
    base = json_ld.get("baseSalary") if json_ld else None
    if not isinstance(base, dict):
        return None
    currency = base.get("currency")
    value = base.get("value")
    if isinstance(value, dict):
        min_value = value.get("minValue")
        max_value = value.get("maxValue")
        if min_value and max_value:
            return f"{currency or ''} {min_value} - {max_value}".strip()
        if min_value or max_value:
            return f"{currency or ''} {min_value or max_value}".strip()
    return None


def _salary_text_from_text(text: str) -> str | None:
    match = re.search(r"([$€£]\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?\s*(?:-|–|to)\s*[$€£]?\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?)", text)
    if match:
        return match.group(1)
    match = re.search(r"([$€£]\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?)", text)
    if match:
        return match.group(1)
    for word in ("Competitive", "No salary listed"):
        if word.lower() in text.lower():
            return word
    return None


def _parse_salary(value: str) -> tuple[int | None, int | None, str | None] | None:
    salary_part = _salary_text_from_text(value) or value
    if not re.search(r"[$€£]|\b(?:USD|EUR|GBP)\b", salary_part, re.IGNORECASE):
        return None
    currency = None
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in salary_part:
            currency = code
            break
    if currency is None:
        match = re.search(r"\b(USD|EUR|GBP)\b", salary_part, re.IGNORECASE)
        currency = match.group(1).upper() if match else None
    numbers = re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([Kk])?", salary_part)
    if not numbers:
        return None
    parsed = [_salary_number(number, suffix) for number, suffix in numbers[:2]]
    return parsed[0], parsed[1] if len(parsed) > 1 else parsed[0], currency


def _salary_number(number: str, suffix: str) -> int:
    value = float(number.replace(",", ""))
    if suffix.lower() == "k":
        value *= 1000
    return int(value)


def _normalize_employment_type(value: str) -> str | None:
    lower = value.lower().replace("_", "-")
    if "full" in lower:
        return "full_time"
    if "part" in lower:
        return "part_time"
    if "contract" in lower:
        return "contract"
    if "intern" in lower:
        return "internship"
    if "temporary" in lower:
        return "temporary"
    if "co-founder" in lower or "cofounder" in lower:
        return "cofounder"
    return "other" if value.strip() else None


def _safe_apply_url(value: str) -> str | None:
    if SENSITIVE_QUERY_RE.search(value):
        return None
    normalized = normalize_job_url(value)
    return normalized.canonical_url if normalized.valid else None


def _title_from_slug(canonical_url: str) -> str | None:
    parsed = parse_yc_job_url(canonical_url)
    if not parsed:
        return None
    slug = parsed.job_path
    bits = slug.split("-", 1)
    words = bits[1] if len(bits) == 2 else slug
    return " ".join(word.capitalize() for word in unquote(words).split("-") if word)


def _clean_title(value: str) -> str:
    text = _normalize_ws(value)
    text = re.sub(r"\s+\|\s+Y Combinator.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+at\s+.+$", "", text, flags=re.IGNORECASE)
    return strip_job_title_action_suffix(text.strip(" -|")) or ""


def _html_to_text(value: str) -> str:
    return _clean_description(BeautifulSoup(value or "", "html.parser").get_text("\n"))


def _clean_description(value: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for raw in value.splitlines():
        line = _normalize_ws(raw)
        if not line:
            continue
        lower = line.lower()
        if lower in seen:
            continue
        if any(token in lower for token in ("recommended jobs", "sign in", "y combinator home", "apply to y combinator")):
            continue
        seen.add(lower)
        lines.append(line)
    return "\n".join(lines).strip()


def _bounded_description(value: str) -> str:
    return value[:MAX_DESCRIPTION_CHARS].rstrip()


def _clean_text(value: str) -> str:
    return _clean_description(value)


def _normalize_ws(value: Any) -> str:
    return re.sub(r"\s+", " ", repair_mojibake(str(value or "")) or "").strip()


def _dedupe_list(items: list[str]) -> list[str]:
    return dedupe_meaningful_entries(items, maximum=30, max_length=120)
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _normalize_ws(item).strip(" -•")
        if not cleaned or len(cleaned) > 80:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= 30:
            break
    return result
