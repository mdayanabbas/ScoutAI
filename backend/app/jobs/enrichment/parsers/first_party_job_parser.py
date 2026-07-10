import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.jobs.enrichment.models import JobDetailExtractionResult, JobFieldValue
from app.jobs.enrichment.parsers.ycombinator_job_parser import classify_role_category
from app.jobs.job_source_detector import compare_registrable_domains, normalize_job_url
from app.utils.enums import RemoteType

PROVIDER = "first_party_job_page"
GENERIC_TITLES = {"careers", "jobs", "open roles", "join our team", "current openings", "open positions"}
CURRENCY_SYMBOLS = {"$": "USD", "\u20ac": "EUR", "\u00a3": "GBP"}
TECH_WORDS = {
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


class FirstPartyJobParser:
    def parse(
        self,
        html: str,
        *,
        source_url: str,
        canonical_url: str,
        company_name: str | None,
        company_domain: str,
    ) -> JobDetailExtractionResult:
        if not html or not html.strip():
            return _empty(source_url, canonical_url, "first_party_job_data_missing")
        soup = BeautifulSoup(html, "html.parser")
        json_postings = _dedupe_postings(_jobposting_json_ld(html))
        listing_signals = _listing_signals(soup, canonical_url, json_postings)
        evidence: dict[str, Any] = {
            "parser": "first_party_job_parser",
            "jobposting_count": len(json_postings),
            "listing_page_signals": listing_signals[:10],
            "strategy": "json_ld" if json_postings else "semantic_html",
        }
        if len(json_postings) > 1:
            return _empty(source_url, canonical_url, "first_party_listing_page_requires_expansion", evidence=evidence)
        json_ld = json_postings[0] if json_postings else {}
        identity_reason = _identity_mismatch(json_ld, soup, company_name, company_domain)
        if identity_reason:
            return _empty(source_url, canonical_url, identity_reason, evidence=evidence)
        if listing_signals and not json_ld:
            return _empty(source_url, canonical_url, "first_party_listing_page_requires_expansion", evidence=evidence)

        for tag in soup(["script", "style", "noscript", "svg", "form", "nav", "footer", "header", "aside"]):
            tag.decompose()
        labels = _labelled_fields(soup)
        text = _clean_description(soup.get_text("\n"))
        title = _title_field(json_ld, soup, canonical_url, company_name)
        if title and str(title.value).strip().lower() in GENERIC_TITLES:
            return _empty(source_url, canonical_url, "first_party_listing_page_requires_expansion", evidence=evidence)
        description = _description_field(json_ld, soup, text)
        location = _location_field(json_ld, labels)
        remote_type = _remote_type_field(json_ld, labels, location)
        employment_type = _employment_type_field(json_ld, labels)
        experience_min, experience_max, seniority = _experience_fields(json_ld, labels, text, title.value if title else None)
        salary_min, salary_max, salary_currency, salary_text = _salary_fields(json_ld, labels, text)
        equity = _equity_field(labels, text)
        visa, work_auth = _visa_fields(labels, text)
        required_skills, technologies = _skills_fields(json_ld, labels, text)
        preferred_skills = _preferred_skills_field(text)
        published_at = _published_at_field(json_ld, labels)
        apply_url = _apply_url_field(json_ld, soup, canonical_url, company_domain)
        raw_role = _field(labels.get("role") or labels.get("department"), 0.85, "labelled_field")
        role_category = _role_category_field(title, raw_role, description)
        job_url = _field(canonical_url, 0.95, "canonical_first_party_url")
        fields = {
            "title": title,
            "description": description,
            "role_category": role_category,
            "location": location,
            "remote_type": remote_type,
            "employment_type": employment_type,
            "experience_min": experience_min,
            "experience_max": experience_max,
            "seniority": seniority,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "salary_text": salary_text,
            "equity_mentioned": equity,
            "apply_url": apply_url,
            "visa_sponsorship": visa,
            "work_authorization": work_auth,
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "technologies": technologies,
            "published_at": published_at,
            "raw_role": raw_role,
            "job_url": job_url,
        }
        confidence = {key: round(value.confidence, 3) for key, value in fields.items() if value}
        important_scores = [
            item.confidence
            for item in (title, description, role_category, location, employment_type)
            if item is not None
        ]
        overall = min(1.0, sum(important_scores) / max(3, len(important_scores))) if important_scores else 0
        evidence["overall_confidence"] = round(overall, 3)
        evidence["detected_labels"] = sorted(labels)
        evidence["extracted_field_names"] = sorted(confidence)
        if not title or title.confidence < 0.75:
            return _empty(source_url, canonical_url, "first_party_job_data_missing", evidence=evidence)
        return JobDetailExtractionResult(
            success=True,
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
            job_url=job_url,
            apply_url=apply_url,
            visa_sponsorship=visa,
            work_authorization=work_auth,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            technologies=technologies,
            published_at=published_at,
            raw_role=raw_role,
            field_confidence=confidence,
            evidence=evidence,
            reason="first_party_job_page_enriched",
        )


def _empty(
    source_url: str,
    canonical_url: str,
    reason: str,
    *,
    evidence: dict[str, Any] | None = None,
) -> JobDetailExtractionResult:
    return JobDetailExtractionResult(
        success=False,
        provider=PROVIDER,
        source_url=source_url,
        canonical_url=canonical_url,
        reason=reason,
        evidence=evidence or {},
    )


def _field(value: Any, confidence: float, source: str, evidence: dict[str, Any] | None = None) -> JobFieldValue | None:
    if value is None or value == "" or value == []:
        return None
    return JobFieldValue(value, confidence, source, evidence or {})


def _jobposting_json_ld(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    postings: list[dict[str, Any]] = []
    for script in soup.find_all("script", type=lambda value: value and "ld+json" in value.lower()):
        try:
            payload = json.loads(script.string or script.get_text() or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        for item in _json_items(payload):
            item_type = item.get("@type")
            if item_type == "JobPosting" or (isinstance(item_type, list) and "JobPosting" in item_type):
                postings.append(item)
    return postings


def _json_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        items: list[dict[str, Any]] = []
        for item in payload:
            items.extend(_json_items(item))
        return items
    return []


def _dedupe_postings(postings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for posting in postings:
        key = "|".join(
            [
                _norm(posting.get("title")),
                _norm(posting.get("datePosted")),
                _norm(_location_text(posting.get("jobLocation"))),
            ]
        )
        unique[key] = posting
    return list(unique.values())


def _listing_signals(soup: BeautifulSoup, canonical_url: str, postings: list[dict[str, Any]]) -> list[str]:
    signals: list[str] = []
    path = normalize_job_url(canonical_url).path or ""
    if path.lower() in {"/careers", "/jobs", "/openings", "/careers/jobs"}:
        signals.append("generic_listing_path")
    text = _norm(" ".join(tag.get_text(" ") for tag in soup.find_all(["h1", "h2"])))
    for phrase in ("open positions", "current openings", "available roles", "join our team"):
        if phrase in text:
            signals.append(f"heading:{phrase}")
    job_links = [
        link
        for link in soup.find_all("a", href=True)
        if re.search(r"\b(engineer|designer|manager|executive|developer|analyst|lead)\b", link.get_text(" "), re.I)
    ]
    if len(job_links) >= 3:
        signals.append("multiple_role_links")
    if len(postings) > 1:
        signals.append("multiple_jobpostings")
    return signals


def _identity_mismatch(
    json_ld: dict[str, Any],
    soup: BeautifulSoup,
    company_name: str | None,
    company_domain: str,
) -> str | None:
    org = json_ld.get("hiringOrganization") if json_ld else None
    org_name = org.get("name") if isinstance(org, dict) else None
    same_as = org.get("sameAs") if isinstance(org, dict) else None
    if same_as and not compare_registrable_domains(normalize_job_url(str(same_as)).normalized_domain, company_domain):
        return "first_party_company_identity_mismatch"
    if org_name and company_name and not _name_matches(org_name, company_name):
        return "first_party_company_identity_mismatch"
    site_name = soup.find("meta", property="og:site_name")
    if site_name and site_name.get("content") and company_name and not _name_matches(site_name["content"], company_name):
        content = _norm(site_name["content"])
        if content not in {"careers", "jobs"}:
            return "first_party_company_identity_mismatch"
    return None


def _name_matches(left: str, right: str) -> bool:
    left_norm = re.sub(r"[^a-z0-9]+", "", left.lower())
    right_norm = re.sub(r"[^a-z0-9]+", "", right.lower())
    return bool(left_norm and right_norm and (left_norm in right_norm or right_norm in left_norm))


def _title_field(json_ld: dict[str, Any], soup: BeautifulSoup, canonical_url: str, company_name: str | None) -> JobFieldValue | None:
    title = _clean_title(json_ld.get("title"), company_name) if json_ld else ""
    if title and title.lower() not in GENERIC_TITLES:
        return _field(title, 1.0, "jobposting_title")
    h1s = [_clean_title(tag.get_text(" "), company_name) for tag in soup.find_all("h1")]
    h1s = [item for item in h1s if item and item.lower() not in GENERIC_TITLES]
    if len(set(h1s)) == 1:
        return _field(h1s[0], 0.96, "primary_heading")
    og = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "title"})
    if og and og.get("content"):
        value = _clean_title(str(og["content"]), company_name)
        if value and value.lower() not in GENERIC_TITLES:
            return _field(value, 0.88, "open_graph")
    doc = soup.find("title")
    if doc:
        value = _clean_title(doc.get_text(" "), company_name)
        if value and value.lower() not in GENERIC_TITLES:
            return _field(value, 0.82, "document_title")
    slug = _title_from_slug(canonical_url)
    return _field(slug, 0.65, "url_slug") if slug else None


def _description_field(json_ld: dict[str, Any], soup: BeautifulSoup, visible_text: str) -> JobFieldValue | None:
    if json_ld.get("description"):
        return _field(_bounded_description(_html_to_text(str(json_ld["description"]))), 0.97, "jobposting_description")
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = _clean_description(main.get_text("\n"))
    if text:
        return _field(_bounded_description(text), 0.88, "main_content")
    if visible_text:
        return _field(_bounded_description(visible_text), 0.75, "visible_text")
    return None


def _labelled_fields(soup: BeautifulSoup) -> dict[str, str]:
    labels: dict[str, str] = {}
    pattern = re.compile(r"^(Location|Job type|Type|Employment|Experience|Department|Role|Compensation|Salary|Skills?|Visa)\s*[:\-]\s*(.+)$", re.I)
    for tag in soup.find_all(["li", "p", "div", "span"]):
        text = _normalize_ws(tag.get_text(" "))
        if len(text) > 600:
            continue
        match = pattern.match(text)
        if match:
            labels[_label_key(match.group(1))] = match.group(2)
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            labels[_label_key(dt.get_text(" "))] = _normalize_ws(dd.get_text(" "))
    return {key: value for key, value in labels.items() if key}


def _label_key(value: str) -> str:
    return {
        "location": "location",
        "job type": "employment_type",
        "type": "employment_type",
        "employment": "employment_type",
        "experience": "experience",
        "department": "department",
        "role": "role",
        "compensation": "compensation",
        "salary": "compensation",
        "skills": "skills",
        "skill": "skills",
        "visa": "visa",
    }.get(_normalize_ws(value).lower(), "")


def _location_field(json_ld: dict[str, Any], labels: dict[str, str]) -> JobFieldValue | None:
    value = labels.get("location") or _location_text(json_ld.get("jobLocation"))
    return _field(value, 0.94 if json_ld.get("jobLocation") else 0.85, "location")


def _location_text(value: Any) -> str | None:
    if isinstance(value, list):
        parts = [_location_text(item) for item in value]
        return " / ".join(item for item in parts if item) or None
    if isinstance(value, dict):
        address = value.get("address") if isinstance(value.get("address"), dict) else value
        parts = [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")]
        return ", ".join(str(part) for part in parts if part) or value.get("name")
    return str(value).strip() if value else None


def _remote_type_field(json_ld: dict[str, Any], labels: dict[str, str], location: JobFieldValue | None) -> JobFieldValue | None:
    structured = " ".join(str(item or "") for item in (json_ld.get("jobLocationType"), json_ld.get("applicantLocationRequirements"), labels.get("location"))).lower()
    if "telecommute" in structured or "remote" in structured:
        return _field(RemoteType.REMOTE_WORLDWIDE.value, 0.92, "remote_signal")
    if "hybrid" in structured:
        return _field(RemoteType.HYBRID.value, 0.9, "remote_signal")
    if "onsite" in structured or "on-site" in structured or "in-person" in structured:
        return _field(RemoteType.ONSITE.value, 0.9, "remote_signal")
    if location and "remote" in str(location.value).lower():
        return _field(RemoteType.REMOTE_WORLDWIDE.value, 0.85, "location")
    return None


def _employment_type_field(json_ld: dict[str, Any], labels: dict[str, str]) -> JobFieldValue | None:
    raw = json_ld.get("employmentType") or labels.get("employment_type")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    normalized = _normalize_employment_type(str(raw)) if raw else None
    return _field(normalized, 0.94, "employment_type", {"raw": raw}) if normalized else None


def _normalize_employment_type(value: str) -> str | None:
    lower = value.lower().replace("_", "-")
    if "full" in lower:
        return "full_time"
    if "part" in lower:
        return "part_time"
    if "contract" in lower or "contractor" in lower:
        return "contract"
    if "temporary" in lower:
        return "temporary"
    if "intern" in lower:
        return "internship"
    if "volunteer" in lower:
        return "volunteer"
    if "per" in lower and "diem" in lower:
        return "per_diem"
    return "other" if value.strip() else None


def _experience_fields(json_ld: dict[str, Any], labels: dict[str, str], text: str, title: str | None) -> tuple[JobFieldValue | None, JobFieldValue | None, JobFieldValue | None]:
    raw = " ".join(str(item or "") for item in (json_ld.get("experienceRequirements"), labels.get("experience"), text[:4000]))
    match = re.search(r"\b(\d+)\s*(?:-|to|\u2013)\s*(\d+)\s*\+?\s+years?", raw, re.I)
    if match:
        return _field(int(match.group(1)), 0.9, "experience_text"), _field(int(match.group(2)), 0.9, "experience_text"), _seniority(title, raw)
    match = re.search(r"\b(\d+)\s*\+\s+years?", raw, re.I)
    if match:
        return _field(int(match.group(1)), 0.9, "experience_text"), None, _seniority(title, raw)
    return None, None, _seniority(title, raw)


def _seniority(title: str | None, text: str) -> JobFieldValue | None:
    value = f"{title or ''} {text[:1000]}".lower()
    for label in ("principal", "staff", "senior", "lead", "manager", "director"):
        if label in value:
            return _field(label, 0.85, "seniority_text")
    if "entry level" in value or "new graduate" in value:
        return _field("entry_level", 0.85, "seniority_text")
    return None


def _salary_fields(json_ld: dict[str, Any], labels: dict[str, str], text: str) -> tuple[JobFieldValue | None, JobFieldValue | None, JobFieldValue | None, JobFieldValue | None]:
    raw = _salary_text_from_json_ld(json_ld) or labels.get("compensation") or _salary_text_from_text(text)
    if not raw:
        return None, None, None, None
    parsed = _parse_salary(raw)
    salary_text = _field(raw, 0.9, "salary_text")
    if parsed is None:
        return None, None, None, salary_text
    minimum, maximum, currency = parsed
    return _field(minimum, 0.9, "salary_text"), _field(maximum, 0.9, "salary_text"), _field(currency, 0.9, "salary_text") if currency else None, salary_text


def _salary_text_from_json_ld(json_ld: dict[str, Any]) -> str | None:
    salary = json_ld.get("baseSalary")
    if not isinstance(salary, dict):
        return None
    currency = salary.get("currency")
    value = salary.get("value")
    if isinstance(value, dict):
        minimum = value.get("minValue")
        maximum = value.get("maxValue") or value.get("value")
        unit = value.get("unitText")
        if minimum or maximum:
            return " ".join(str(item) for item in (currency, minimum, "-", maximum, unit) if item is not None)
    if value:
        return f"{currency or ''} {value}".strip()
    return None


def _salary_text_from_text(text: str) -> str | None:
    match = re.search(r"((?:USD|EUR|GBP|\$|\u20ac|\u00a3)\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?\s*(?:-|to|\u2013)\s*(?:USD|EUR|GBP|\$|\u20ac|\u00a3)?\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?(?:\s*/\s*hour)?)", text, re.I)
    if match:
        return match.group(1)
    match = re.search(r"((?:USD|EUR|GBP|\$|\u20ac|\u00a3)\s?\d[\d,]*(?:\.\d+)?\s?[Kk]?(?:\s*/\s*hour)?)", text, re.I)
    if match:
        return match.group(1)
    return "Competitive" if "competitive" in text.lower() else None


def _parse_salary(value: str) -> tuple[int | None, int | None, str | None] | None:
    if not re.search(r"USD|EUR|GBP|\$|\u20ac|\u00a3", value, re.I):
        return None
    currency = None
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in value:
            currency = code
    match = re.search(r"\b(USD|EUR|GBP)\b", value, re.I)
    if match:
        currency = match.group(1).upper()
    numbers = re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([Kk])?", value)
    if not numbers:
        return None
    values = [_salary_number(number, suffix) for number, suffix in numbers[:2]]
    return values[0], values[1] if len(values) > 1 else values[0], currency


def _salary_number(number: str, suffix: str) -> int:
    value = float(number.replace(",", ""))
    if suffix.lower() == "k":
        value *= 1000
    return int(value)


def _equity_field(labels: dict[str, str], text: str) -> JobFieldValue | None:
    haystack = " ".join([labels.get("compensation", ""), text[:3000]])
    if re.search(r"\b(no equity|without equity)\b", haystack, re.I):
        return _field(False, 0.9, "equity_text")
    if re.search(r"\bequity\b|\d+(?:\.\d+)?%", haystack, re.I):
        return _field(True, 0.85, "equity_text")
    return None


def _visa_fields(labels: dict[str, str], text: str) -> tuple[JobFieldValue | None, JobFieldValue | None]:
    haystack = " ".join([labels.get("visa", ""), text[:4000]])
    lower = haystack.lower()
    if "unable to sponsor" in lower or "no visa" in lower:
        return _field("does_not_sponsor", 0.9, "visa_text"), None
    if "visa sponsorship available" in lower or "will sponsor" in lower:
        return _field("sponsors", 0.9, "visa_text"), None
    if "authorized to work" in lower or "work authorization" in lower:
        return _field("existing_authorization_required", 0.85, "visa_text"), _field(haystack[:255], 0.8, "authorization_text")
    return None, None


def _skills_fields(json_ld: dict[str, Any], labels: dict[str, str], text: str) -> tuple[JobFieldValue | None, JobFieldValue | None]:
    raw = json_ld.get("skills") or labels.get("skills") or ""
    if isinstance(raw, list):
        values = raw
    else:
        values = re.split(r"[,;|/]", str(raw))
    skills = _dedupe(values)
    technologies = [word for word in sorted(TECH_WORDS) if re.search(rf"(?<![\w.+#]){re.escape(word)}(?![\w.+#])", text, re.I)]
    return _field(skills, 0.85, "skills") if skills else None, _field(technologies, 0.75, "technology_text") if technologies else None


def _preferred_skills_field(text: str) -> JobFieldValue | None:
    match = re.search(r"(?is)(nice to have|preferred qualifications?)\s*[:\n]\s*(.+?)(?:\n[A-Z][^\n]{1,60}\n|$)", text)
    if not match:
        return None
    return _field(_dedupe(re.split(r"[,;\n|-]", match.group(2)))[:20], 0.75, "preferred_section")


def _published_at_field(json_ld: dict[str, Any], labels: dict[str, str]) -> JobFieldValue | None:
    value = json_ld.get("datePosted") or labels.get("posted")
    if not value:
        return None
    try:
        return _field(datetime.fromisoformat(str(value).replace("Z", "+00:00")), 0.95, "published_at")
    except ValueError:
        return None


def _apply_url_field(json_ld: dict[str, Any], soup: BeautifulSoup, canonical_url: str, company_domain: str) -> JobFieldValue | None:
    raw = json_ld.get("url") if json_ld else None
    if not raw:
        for link in soup.find_all("a", href=True):
            if "apply" in _norm(link.get_text(" ")):
                raw = urljoin(canonical_url, link["href"])
                break
    normalized = normalize_job_url(str(raw)) if raw else None
    if normalized and normalized.valid and normalized.canonical_url:
        return _field(normalized.canonical_url, 0.85 if compare_registrable_domains(normalized.normalized_domain, company_domain) else 0.7, "apply_url")
    return _field(canonical_url, 0.7, "canonical_job_url")


def _role_category_field(title: JobFieldValue | None, raw_role: JobFieldValue | None, description: JobFieldValue | None) -> JobFieldValue | None:
    category = classify_role_category(
        title.value if title else None,
        raw_role.value if raw_role else None,
        description.value if description else None,
    )
    return _field(category, 0.95 if category != "other" else 0.65, "deterministic_role_classifier")


def _clean_title(value: Any, company_name: str | None) -> str:
    text = _normalize_ws(value)
    if company_name:
        text = re.sub(rf"\s+[-|]\s+{re.escape(company_name)}.*$", "", text, flags=re.I)
        text = re.sub(rf"\s+at\s+{re.escape(company_name)}.*$", "", text, flags=re.I)
    text = re.sub(r"\s+[-|]\s+(careers|jobs).*$", "", text, flags=re.I)
    return text.strip(" -|")


def _title_from_slug(canonical_url: str) -> str | None:
    path = normalize_job_url(canonical_url).path or ""
    slug = unquote(path.rstrip("/").split("/")[-1])
    if not slug or slug.lower() in {"careers", "jobs", "openings"}:
        return None
    words = [word for word in re.split(r"[-_]+", slug) if word and not word.isdigit()]
    if len(words) < 2:
        return None
    return " ".join(word.upper() if word in {"ai", "ml"} else word.capitalize() for word in words)


def _html_to_text(value: str) -> str:
    soup = BeautifulSoup(value or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return _clean_description(soup.get_text("\n"))


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
        if any(token in lower for token in ("cookie", "privacy policy", "view all jobs", "similar jobs")):
            continue
        seen.add(lower)
        lines.append(line)
    return "\n".join(lines).strip()


def _bounded_description(value: str) -> str:
    return value[: get_settings().FIRST_PARTY_JOB_MAX_DESCRIPTION_CHARS].rstrip()


def _dedupe(items: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _normalize_ws(item).strip(" -*")
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


def _normalize_ws(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm(value: Any) -> str:
    return _normalize_ws(value).lower()

