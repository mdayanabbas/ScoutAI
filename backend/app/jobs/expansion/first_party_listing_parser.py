import json
import re
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.jobs.enrichment.parsers.ycombinator_job_parser import is_generic_job_title
from app.jobs.expansion.first_party_listing_models import (
    FirstPartyListingCandidate,
    FirstPartyListingExtractionResult,
)
from app.jobs.job_source_detector import (
    compare_registrable_domains,
    normalize_job_url,
    parse_ashby_job_url,
)

GENERIC_PATHS = {"/careers", "/jobs", "/openings", "/join-us", "/work-with-us", "/careers/jobs"}
BLOCKED_PATH_TOKENS = {
    "account",
    "admin",
    "blog",
    "customer",
    "login",
    "logout",
    "privacy",
    "signin",
    "signup",
    "story",
    "terms",
}
EXTERNAL_ATS_DOMAINS = {
    "jobs.ashbyhq.com": "ashby",
    "greenhouse.io": "greenhouse",
    "boards.greenhouse.io": "greenhouse",
    "lever.co": "lever",
    "jobs.lever.co": "lever",
    "workable.com": "workable",
    "apply.workable.com": "workable",
}
ROLE_WORD_RE = re.compile(
    r"\b(engineer|developer|designer|product manager|account executive|sales|marketing|"
    r"growth|operations|recruiter|data scientist|analyst|lead|manager|architect|"
    r"customer success|solutions|security|devops|sre|founding)\b",
    re.I,
)


class FirstPartyListingParser:
    def parse(
        self,
        html: str,
        *,
        source_url: str,
        canonical_url: str,
        company_name: str | None,
        company_domain: str,
    ) -> FirstPartyListingExtractionResult:
        if not html or not html.strip():
            return FirstPartyListingExtractionResult(
                source_url=source_url,
                canonical_url=canonical_url,
                reason="first_party_listing_no_roles",
                warnings=["empty_html"],
            )
        try:
            soup = BeautifulSoup(html, "html.parser")
            structured = _structured_candidates(html, canonical_url, company_name, company_domain)
            html_candidates = _html_candidates(soup, canonical_url, company_domain)
            candidates = _dedupe_candidates([*structured, *html_candidates])
            settings = get_settings()
            limited = candidates[: settings.FIRST_PARTY_LISTING_MAX_LINKS]
            valid = [item for item in limited if not item.rejection_reason]
            if not valid:
                reason = "first_party_listing_candidates_invalid" if limited else "first_party_listing_no_roles"
                return FirstPartyListingExtractionResult(
                    source_url=source_url,
                    canonical_url=canonical_url,
                    candidates=limited[:25],
                    candidate_count=len(limited),
                    parser_strategy=_strategy(structured, html_candidates),
                    listing_detected=False,
                    confidence=0.0,
                    reason=reason,
                    evidence=_evidence(limited),
                )
            confidence = max(item.confidence for item in valid)
            return FirstPartyListingExtractionResult(
                source_url=source_url,
                canonical_url=canonical_url,
                candidates=limited,
                candidate_count=len(limited),
                parser_strategy=_strategy(structured, html_candidates),
                listing_detected=True,
                confidence=confidence,
                reason="first_party_listing_detected",
                evidence=_evidence(limited),
            )
        except Exception:
            return FirstPartyListingExtractionResult(
                source_url=source_url,
                canonical_url=canonical_url,
                reason="first_party_listing_parser_error",
            )


def _structured_candidates(
    html: str,
    canonical_url: str,
    company_name: str | None,
    company_domain: str,
) -> list[FirstPartyListingCandidate]:
    postings = _dedupe_postings(_jobposting_json_ld(html))
    candidates: list[FirstPartyListingCandidate] = []
    seen_listing_url = False
    for posting in postings:
        title = _clean_title(posting.get("title"), company_name)
        if _org_mismatch(posting, company_name, company_domain):
            candidates.append(
                FirstPartyListingCandidate(
                    title=title,
                    source_strategy="json_ld_jobposting",
                    confidence=0.0,
                    rejected_signals=["hiring_organization_mismatch"],
                    rejection_reason="first_party_listing_company_mismatch",
                    structured_data=_bounded_structured(posting),
                )
            )
            continue
        raw_url = _posting_url(posting)
        normalized = _candidate_url(raw_url, canonical_url, company_domain)
        identifier = _posting_identifier(posting)
        rejected: list[str] = []
        confidence = 0.92
        if _generic_title(title):
            rejected.append("generic_title")
        if raw_url and normalized.rejection_reason:
            rejected.append(normalized.rejection_reason)
        if not normalized.canonical_url and not identifier:
            rejected.append("missing_stable_identity")
        if normalized.canonical_url == canonical_url:
            if seen_listing_url or not identifier:
                rejected.append("duplicate_listing_page_identity")
            seen_listing_url = True
        candidates.append(
            FirstPartyListingCandidate(
                title=title,
                original_url=raw_url,
                canonical_url=normalized.canonical_url,
                source_strategy="json_ld_jobposting",
                posting_identifier=identifier,
                location=_location_text(posting.get("jobLocation")),
                employment_type=_employment_type(posting.get("employmentType")),
                description_excerpt=_excerpt(_html_to_text(str(posting.get("description") or ""))),
                confidence=0.0 if rejected else confidence,
                matched_signals=["json_ld_jobposting", "stable_provider_identifier"] if identifier else ["json_ld_jobposting"],
                rejected_signals=rejected[:10],
                rejection_reason=rejected[0] if rejected else None,
                structured_data=_bounded_structured(posting),
            )
        )
    return candidates


def _html_candidates(
    soup: BeautifulSoup,
    canonical_url: str,
    company_domain: str,
) -> list[FirstPartyListingCandidate]:
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "aside"]):
        tag.decompose()
    candidates: list[FirstPartyListingCandidate] = []
    for container in soup.find_all(["article", "li", "tr", "section", "div"]):
        if _ignored_container(container):
            continue
        link = container.find("a", href=True)
        if not link:
            continue
        text = _normalize_ws(container.get_text(" "))
        if len(text) > 1200:
            continue
        title = _best_title(container, link)
        if not _looks_like_role(title):
            continue
        candidate = _candidate_from_link(
            title,
            link.get("href"),
            canonical_url,
            company_domain,
            "semantic_role_card",
            text=text,
            confidence=0.86,
            matched=["explicit_role_card"],
        )
        candidates.append(candidate)

    for link in soup.find_all("a", href=True):
        if _ignored_container(link):
            continue
        title = _clean_title(link.get_text(" "), None)
        if not _looks_like_role(title):
            continue
        candidate = _candidate_from_link(
            title,
            link.get("href"),
            canonical_url,
            company_domain,
            "career_section_anchor",
            confidence=0.78,
            matched=["role_anchor_text"],
        )
        candidates.append(candidate)

    return candidates


def _candidate_from_link(
    title: str | None,
    href: str | None,
    canonical_url: str,
    company_domain: str,
    strategy: str,
    *,
    text: str | None = None,
    confidence: float,
    matched: list[str],
) -> FirstPartyListingCandidate:
    normalized = _candidate_url(href, canonical_url, company_domain)
    rejected: list[str] = []
    if _generic_title(title):
        rejected.append("generic_title")
    if normalized.rejection_reason:
        rejected.append(normalized.rejection_reason)
    if not _more_specific_path(normalized.canonical_url, canonical_url) and not parse_ashby_job_url(normalized.canonical_url):
        rejected.append("duplicate_or_generic_parent_path")
    department, location, employment_type = _metadata_from_text(text or "")
    path_signal = "job_like_url_path" if _job_like_path(normalized.canonical_url) else None
    matched_signals = [*matched]
    if path_signal:
        matched_signals.append(path_signal)
    if location:
        matched_signals.append("location_metadata")
    return FirstPartyListingCandidate(
        title=title,
        original_url=href,
        canonical_url=normalized.canonical_url,
        source_strategy=strategy,
        department=department,
        location=location,
        employment_type=employment_type,
        description_excerpt=_excerpt(text or ""),
        confidence=0.0 if rejected else min(0.95, confidence + (0.05 if path_signal else 0)),
        matched_signals=matched_signals[:10],
        rejected_signals=rejected[:10],
        rejection_reason=rejected[0] if rejected else None,
    )


class _URLResult:
    def __init__(self, canonical_url: str | None = None, rejection_reason: str | None = None) -> None:
        self.canonical_url = canonical_url
        self.rejection_reason = rejection_reason


def _candidate_url(raw_url: str | None, canonical_url: str, company_domain: str) -> _URLResult:
    if not raw_url:
        return _URLResult(None, "missing_url")
    absolute = urljoin(canonical_url, raw_url)
    parsed = urlparse(absolute)
    if parsed.fragment and not parsed.path.strip("/"):
        return _URLResult(None, "navigation_fragment")
    normalized = normalize_job_url(absolute)
    if not normalized.valid or not normalized.canonical_url:
        return _URLResult(None, normalized.reason)
    domain = normalized.normalized_domain
    ats = _external_ats_provider(domain)
    if ats:
        ashby = parse_ashby_job_url(normalized.canonical_url)
        if ats == "ashby" and ashby and ashby.exact_posting:
            return _URLResult(ashby.canonical_url)
        return _URLResult(normalized.canonical_url, "external_ats_provider_not_supported")
    if not compare_registrable_domains(domain, company_domain):
        return _URLResult(None, "domain_mismatch")
    path = (normalized.path or "").lower()
    if path in GENERIC_PATHS:
        return _URLResult(normalized.canonical_url, "generic_listing_path")
    if any(f"/{token}" in path or path.endswith(f"/{token}") for token in BLOCKED_PATH_TOKENS):
        return _URLResult(normalized.canonical_url, "blocked_path")
    if re.search(r"\.(pdf|doc|docx|zip)$", path):
        return _URLResult(normalized.canonical_url, "file_download")
    return _URLResult(normalized.canonical_url)


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
                _norm(_posting_identifier(posting)),
                _norm(_posting_url(posting)),
                _norm(_location_text(posting.get("jobLocation"))),
            ]
        )
        unique[key] = posting
    return list(unique.values())


def _dedupe_candidates(candidates: list[FirstPartyListingCandidate]) -> list[FirstPartyListingCandidate]:
    unique: dict[str, FirstPartyListingCandidate] = {}
    for candidate in candidates:
        key = candidate.canonical_url or candidate.posting_identifier or f"{_norm(candidate.title)}:{candidate.source_strategy}"
        existing = unique.get(key)
        if existing is None or candidate.confidence > existing.confidence:
            unique[key] = candidate
    return list(unique.values())


def _posting_url(posting: dict[str, Any]) -> str | None:
    raw = posting.get("url") or posting.get("sameAs") or posting.get("directApply")
    return str(raw).strip() if raw and not isinstance(raw, bool) else None


def _posting_identifier(posting: dict[str, Any]) -> str | None:
    identifier = posting.get("identifier")
    if isinstance(identifier, dict):
        value = identifier.get("value") or identifier.get("@id")
    else:
        value = identifier
    return str(value).strip()[:160] if value else None


def _org_mismatch(posting: dict[str, Any], company_name: str | None, company_domain: str) -> bool:
    org = posting.get("hiringOrganization")
    if not isinstance(org, dict):
        return False
    same_as = org.get("sameAs")
    if same_as and not compare_registrable_domains(normalize_job_url(str(same_as)).normalized_domain, company_domain):
        return True
    name = org.get("name")
    return bool(name and company_name and not _name_matches(str(name), company_name))


def _external_ats_provider(domain: str | None) -> str | None:
    if not domain:
        return None
    for suffix, provider in EXTERNAL_ATS_DOMAINS.items():
        if domain == suffix or domain.endswith(f".{suffix}"):
            return provider
    return None


def _more_specific_path(child_url: str | None, parent_url: str) -> bool:
    if not child_url:
        return False
    child = normalize_job_url(child_url)
    parent = normalize_job_url(parent_url)
    if not child.valid or not parent.valid:
        return False
    if child.canonical_url == parent.canonical_url:
        return False
    child_path = child.path or ""
    parent_path = parent.path or ""
    return len([part for part in child_path.split("/") if part]) > len([part for part in parent_path.split("/") if part])


def _job_like_path(url: str | None) -> bool:
    path = (normalize_job_url(url).path or "").lower()
    return bool(re.search(r"/(job|jobs|career|careers|opening|openings|role|positions)/", f"{path}/"))


def _ignored_container(tag: Any) -> bool:
    for parent in [tag, *list(getattr(tag, "parents", []))[:4]]:
        name = getattr(parent, "name", "")
        if name in {"nav", "footer", "header", "aside"}:
            return True
        classes = " ".join(parent.get("class", []) if hasattr(parent, "get") else [])
        marker = f"{parent.get('id', '')} {classes}".lower() if hasattr(parent, "get") else ""
        if any(token in marker for token in ("nav", "footer", "blog", "customer", "story", "social", "privacy")):
            return True
    return False


def _best_title(container: Any, link: Any) -> str:
    for tag_name in ("h1", "h2", "h3", "h4", "strong"):
        tag = container.find(tag_name)
        if tag:
            title = _clean_title(tag.get_text(" "), None)
            if _looks_like_role(title):
                return title
    return _clean_title(link.get_text(" "), None)


def _metadata_from_text(text: str) -> tuple[str | None, str | None, str | None]:
    department = _label_value(text, ("Department", "Team"))
    location = _label_value(text, ("Location",))
    employment = _label_value(text, ("Type", "Employment", "Job type"))
    return department, location, employment


def _label_value(text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        match = re.search(rf"{label}\s*[:\-]\s*([^|,\n]{{2,80}})", text, re.I)
        if match:
            return _normalize_ws(match.group(1))
    return None


def _location_text(value: Any) -> str | None:
    if isinstance(value, list):
        return " / ".join(item for item in (_location_text(part) for part in value) if item) or None
    if isinstance(value, dict):
        address = value.get("address") if isinstance(value.get("address"), dict) else value
        parts = [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")]
        return ", ".join(str(part) for part in parts if part) or value.get("name")
    return str(value).strip() if value else None


def _employment_type(value: Any) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value).lower().replace("_", "-") if value else None


def _bounded_structured(posting: dict[str, Any]) -> dict[str, Any]:
    kept = {
        key: posting.get(key)
        for key in ("title", "identifier", "datePosted", "employmentType", "jobLocation", "url", "baseSalary", "hiringOrganization", "directApply")
        if key in posting
    }
    description = _html_to_text(str(posting.get("description") or ""))
    if description:
        kept["description_excerpt"] = _excerpt(description)
    return kept


def _html_to_text(value: str) -> str:
    soup = BeautifulSoup(value or "", "html.parser")
    return _normalize_ws(soup.get_text(" "))


def _clean_title(value: Any, company_name: str | None) -> str:
    text = _normalize_ws(value)
    if company_name:
        text = re.sub(rf"\s+[-|]\s+{re.escape(company_name)}.*$", "", text, flags=re.I)
        text = re.sub(rf"\s+at\s+{re.escape(company_name)}.*$", "", text, flags=re.I)
    text = re.sub(r"\s+[-|]\s+(careers|jobs|job openings).*$", "", text, flags=re.I)
    return unquote(text).strip(" -|")


def _looks_like_role(title: str | None) -> bool:
    if not title or _generic_title(title):
        return False
    if len(title) > 120 or len(title.split()) > 12:
        return False
    return bool(ROLE_WORD_RE.search(title))


def _generic_title(value: str | None) -> bool:
    if not value:
        return True
    lower = _norm(value)
    return is_generic_job_title(lower) or lower in {
        "apply now",
        "careers",
        "current openings",
        "details",
        "jobs",
        "join our team",
        "learn more",
        "open roles",
        "view position",
    }


def _name_matches(left: str, right: str) -> bool:
    left_norm = re.sub(r"[^a-z0-9]+", "", left.lower())
    right_norm = re.sub(r"[^a-z0-9]+", "", right.lower())
    return bool(left_norm and right_norm and (left_norm in right_norm or right_norm in left_norm))


def _strategy(structured: list[FirstPartyListingCandidate], html: list[FirstPartyListingCandidate]) -> str:
    if any(not item.rejection_reason for item in structured):
        return "json_ld_jobposting"
    if any(item.source_strategy == "semantic_role_card" for item in html):
        return "semantic_role_card"
    if html:
        return "career_section_anchor"
    return "none"


def _evidence(candidates: list[FirstPartyListingCandidate]) -> dict[str, Any]:
    return {
        "candidate_count": len(candidates),
        "candidates": [
            {
                "title": item.title,
                "canonical_url": item.canonical_url,
                "source_strategy": item.source_strategy,
                "confidence": item.confidence,
                "rejection_reason": item.rejection_reason,
                "matched_signals": item.matched_signals[:8],
                "rejected_signals": item.rejected_signals[:8],
            }
            for item in candidates[:25]
        ],
    }


def _excerpt(value: str, maximum: int = 500) -> str | None:
    text = _normalize_ws(value)
    return text[:maximum] if text else None


def _normalize_ws(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm(value: Any) -> str:
    return _normalize_ws(value).lower()
