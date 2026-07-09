import json
import re
from dataclasses import dataclass, field
from html import unescape
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.enrichment.domain_extractor import (
    is_allowed_company_domain,
    is_platform_or_shared_domain,
    is_valid_hostname,
    normalize_domain_proposal,
)
from app.utils.urls import normalize_domain

BLOCKED_PROFILE_DOMAINS = {
    "account.ycombinator.com",
    "apply.ycombinator.com",
    "apps.apple.com",
    "ashbyhq.com",
    "bookface.ycombinator.com",
    "cal.com",
    "calendly.com",
    "crunchbase.com",
    "deals.ycombinator.com",
    "facebook.com",
    "forbes.com",
    "github.com",
    "github.io",
    "greenhouse.io",
    "instagram.com",
    "lever.co",
    "linkedin.com",
    "maps.apple.com",
    "maps.google.com",
    "medium.com",
    "news.ycombinator.com",
    "notion.site",
    "notion.so",
    "play.google.com",
    "prnewswire.com",
    "producthunt.com",
    "techcrunch.com",
    "twitter.com",
    "startupschool.com",
    "startupschool.org",
    "workatastartup.com",
    "x.com",
    "ycombinator.com",
    "youtube.com",
    "youtu.be",
}

URLISH_RE = re.compile(r"^(?:https?://)?(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/.*)?$", re.I)
WEBSITE_LABEL_RE = re.compile(r"\b(company website|visit website|website|homepage)\b", re.I)
GLOBAL_NAV_TEXT_RE = re.compile(
    r"^(?:startup school|yc program|work at a startup|co-founder matching|"
    r"startup directory|startup library|investors|demo day|hacker news|"
    r"launch yc|yc deals|yc blog|bookface|log in)$",
    re.I,
)


@dataclass(frozen=True)
class YCWebsiteCandidate:
    url: str
    domain: str
    root_domain: str
    source: str
    confidence: float
    evidence: str
    anchor_text: str | None = None
    original_href: str | None = None
    context: str | None = None


@dataclass(frozen=True)
class YCProfileParseResult:
    resolved: bool
    proposed_website_url: str | None = None
    proposed_domain: str | None = None
    company_name: str | None = None
    description: str | None = None
    location: str | None = None
    batch: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class AnchorInfo:
    index: int
    href: str
    normalized_url: str | None
    domain: str | None
    root_domain: str | None
    text: str
    context: str
    in_company_content: bool
    rejected_reason: str | None = None


def parse_yc_company_profile(html: str, profile_url: str) -> YCProfileParseResult:
    soup = BeautifulSoup(html or "", "html.parser")
    metadata = _extract_metadata(soup)
    anchors = _inspect_anchors(soup, profile_url)
    rejected = [
        _anchor_evidence(anchor)
        for anchor in anchors
        if anchor.rejected_reason is not None
    ]
    stats = {
        "anchors_inspected": len(anchors),
        "external_anchors": sum(1 for anchor in anchors if anchor.domain),
    }

    strategies = [
        ("structured_official_website", _structured_candidates(soup)),
        ("yc_header_official_website", _header_anchor_candidates(anchors)),
        ("labelled_website_link", _labelled_anchor_candidates(anchors)),
        ("unique_external_root_domain", _fallback_anchor_candidates(anchors)),
    ]
    for strategy, candidates in strategies:
        selected, reason, consolidated = _select_candidate(candidates)
        evidence = {
            "profile_url": profile_url,
            "extraction_strategy": strategy,
            "stats": {
                **stats,
                "allowed_company_domain_candidates": len(candidates),
            },
            "website_candidates": [
                _candidate_evidence(candidate) for candidate in consolidated
            ],
            "ambiguity_candidate_domains": [
                candidate.root_domain for candidate in consolidated
            ],
            "rejected_candidates": rejected,
        }
        if selected is not None:
            return YCProfileParseResult(
                resolved=True,
                proposed_website_url=selected.url,
                proposed_domain=selected.root_domain,
                confidence=selected.confidence,
                evidence={
                    **evidence,
                    "selected": _candidate_evidence(selected),
                },
                reason=selected.evidence,
                **metadata,
            )
        if reason == "ambiguous_yc_profile_domains":
            return YCProfileParseResult(
                resolved=False,
                evidence=evidence,
                reason=reason,
                **metadata,
            )

    return YCProfileParseResult(
        resolved=False,
        evidence={
            "profile_url": profile_url,
            "extraction_strategy": None,
            "stats": {
                **stats,
                "allowed_company_domain_candidates": 0,
            },
            "website_candidates": [],
            "rejected_candidates": rejected,
        },
        reason="yc_official_website_missing",
        **metadata,
    )


def _extract_metadata(soup: BeautifulSoup) -> dict[str, str | None]:
    data: dict[str, str | None] = {
        "company_name": None,
        "description": None,
        "location": None,
        "batch": None,
    }
    if title := soup.find("h1"):
        data["company_name"] = _clean_text(title.get_text(" "))
    if description := soup.find("meta", attrs={"name": "description"}):
        data["description"] = _clean_text(description.get("content"))

    text = soup.get_text(" ")
    for marker, key in [
        ("Location", "location"),
        ("Batch", "batch"),
    ]:
        value = _text_after_marker(text, marker)
        if value:
            data[key] = value
    return data


def _structured_candidates(soup: BeautifulSoup) -> list[YCWebsiteCandidate]:
    candidates: list[YCWebsiteCandidate] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        for value in _structured_values(_parse_json(script.string), allow_org_url=True):
            candidate = _candidate_from_url(
                value,
                source="structured_official_website",
                confidence=0.99,
                evidence="explicit structured official website",
            )
            if candidate:
                candidates.append(candidate)

    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data is not None:
        for value in _structured_values(_parse_json(next_data.string)):
            candidate = _candidate_from_url(
                value,
                source="embedded_structured_data",
                confidence=0.99,
                evidence="explicit structured official website",
            )
            if candidate:
                candidates.append(candidate)
    return candidates


def _header_anchor_candidates(anchors: list[AnchorInfo]) -> list[YCWebsiteCandidate]:
    candidates: list[YCWebsiteCandidate] = []
    for anchor in anchors:
        if anchor.rejected_reason or not anchor.normalized_url or not anchor.domain:
            continue
        if not anchor.in_company_content or not _is_company_header_context(anchor.context):
            continue
        if anchor.index > _top_profile_anchor_limit(anchors):
            continue
        if not _text_domain_matches_href(anchor.text, anchor.domain):
            continue
        candidate = _candidate_from_url(
            anchor.normalized_url,
            source="yc_header_official_website",
            confidence=0.99,
            evidence="company profile header official website",
            anchor=anchor,
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def _labelled_anchor_candidates(anchors: list[AnchorInfo]) -> list[YCWebsiteCandidate]:
    candidates: list[YCWebsiteCandidate] = []
    for anchor in anchors:
        if anchor.rejected_reason or not anchor.normalized_url:
            continue
        if not anchor.in_company_content:
            continue
        if not WEBSITE_LABEL_RE.search(anchor.text):
            continue
        candidate = _candidate_from_url(
            anchor.normalized_url,
            source="labelled_website_link",
            confidence=0.95,
            evidence="clearly labelled profile website link",
            anchor=anchor,
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def _fallback_anchor_candidates(anchors: list[AnchorInfo]) -> list[YCWebsiteCandidate]:
    candidates: list[YCWebsiteCandidate] = []
    for anchor in anchors:
        if anchor.rejected_reason or not anchor.normalized_url:
            continue
        if not anchor.in_company_content:
            continue
        if _weak_external_context(anchor):
            continue
        candidate = _candidate_from_url(
            anchor.normalized_url,
            source="unique_external_root_domain",
            confidence=0.90,
            evidence="unique strongly scored external company link",
            anchor=anchor,
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def _inspect_anchors(soup: BeautifulSoup, profile_url: str) -> list[AnchorInfo]:
    anchors: list[AnchorInfo] = []
    for index, link in enumerate(soup.find_all("a", href=True)):
        href = str(link.get("href") or "")
        text = _clean_text(link.get_text(" ")) or ""
        context = _context_hint(link)
        in_company_content = _is_company_content_anchor(link)
        normalized_url, domain, root_domain, reason = _normalize_anchor_url(
            href, profile_url, context
        )
        chrome_reason = _global_chrome_reason(link, text, domain)
        if chrome_reason:
            normalized_url = None
            reason = chrome_reason
        anchors.append(
            AnchorInfo(
                index=index,
                href=href,
                normalized_url=normalized_url,
                domain=domain,
                root_domain=root_domain,
                text=text,
                context=context,
                in_company_content=in_company_content,
                rejected_reason=reason,
            )
        )
    return anchors


def _normalize_anchor_url(
    href: str, profile_url: str, context: str
) -> tuple[str | None, str | None, str | None, str | None]:
    decoded = unescape(href or "").strip()
    if not decoded:
        return None, None, None, "malformed_url"
    lowered = decoded.lower()
    if lowered.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None, None, None, "malformed_url"

    absolute = urljoin(profile_url, decoded)
    absolute, _fragment = urldefrag(absolute)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None, None, None, "malformed_url"

    domain = normalize_domain(parsed.hostname).lower().rstrip(".")
    if not is_valid_hostname(domain):
        return None, None, None, "malformed_url"
    reason = _rejection_reason(domain, absolute, context)
    if reason:
        return None, domain, _root_domain(domain), reason

    path = parsed.path.rstrip("/")
    normalized_url = f"{parsed.scheme}://{domain}{path}"
    if parsed.query:
        normalized_url = f"{normalized_url}?{parsed.query}"
    return normalized_url, domain, _root_domain(domain), None


def _candidate_from_url(
    value: str,
    source: str,
    confidence: float,
    evidence: str,
    anchor: AnchorInfo | None = None,
) -> YCWebsiteCandidate | None:
    url = unescape(value).strip()
    domain = normalize_domain_proposal(url)
    if not domain or not _allowed_profile_domain(domain):
        return None
    root_domain = _root_domain(domain)
    return YCWebsiteCandidate(
        url=_canonical_company_url(url, domain, root_domain),
        domain=domain,
        root_domain=root_domain,
        source=source,
        confidence=confidence,
        evidence=evidence,
        anchor_text=anchor.text if anchor else None,
        original_href=anchor.href if anchor else value,
        context=anchor.context if anchor else None,
    )


def _select_candidate(
    candidates: list[YCWebsiteCandidate],
) -> tuple[YCWebsiteCandidate | None, str | None, list[YCWebsiteCandidate]]:
    grouped: dict[str, YCWebsiteCandidate] = {}
    for candidate in sorted(
        candidates, key=lambda item: (_is_root_url(item.url, item.root_domain), item.confidence), reverse=True
    ):
        grouped.setdefault(candidate.root_domain, candidate)

    consolidated = list(grouped.values())
    if not consolidated:
        return None, "yc_official_website_missing", []
    if len(consolidated) > 1:
        return None, "ambiguous_yc_profile_domains", consolidated
    return consolidated[0], None, consolidated


def _structured_values(data: Any, allow_org_url: bool = False) -> list[str]:
    values: list[str] = []
    if isinstance(data, dict):
        is_org = _is_organization_like(data)
        for key, value in data.items():
            if key in {
                "website",
                "websiteUrl",
                "website_url",
                "companyUrl",
                "homepage",
                "homepageUrl",
            } and isinstance(value, str):
                values.append(value)
            elif allow_org_url and is_org and key == "url" and isinstance(value, str):
                values.append(value)
            elif isinstance(value, (dict, list)):
                values.extend(_structured_values(value, allow_org_url=allow_org_url))
    elif isinstance(data, list):
        for item in data:
            values.extend(_structured_values(item, allow_org_url=allow_org_url))
    return values


def _is_organization_like(data: dict[str, Any]) -> bool:
    raw_type = data.get("@type") or data.get("type")
    types = raw_type if isinstance(raw_type, list) else [raw_type]
    normalized = {str(item).lower() for item in types if item}
    return bool(
        normalized
        & {
            "organization",
            "corporation",
            "company",
            "localbusiness",
            "startup",
        }
    )


def _parse_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _rejection_reason(domain: str, url: str, context: str) -> str | None:
    value = domain.lower()
    lowered = f"{url} {context}".lower()
    if value in {
        "startupschool.org",
        "startupschool.com",
        "workatastartup.com",
    } or value == "ycombinator.com" or value.endswith(".ycombinator.com"):
        return "yc_ecosystem_link"
    if "founder" in lowered and value in {"linkedin.com", "x.com", "twitter.com"}:
        return "social_platform"
    if any(value == blocked or value.endswith(f".{blocked}") for blocked in BLOCKED_PROFILE_DOMAINS):
        if value in {"github.com", "linkedin.com", "x.com", "twitter.com", "facebook.com", "instagram.com", "youtube.com", "youtu.be"}:
            return "social_platform"
        if value in {"ashbyhq.com", "greenhouse.io", "lever.co"} or value.endswith((".ashbyhq.com", ".greenhouse.io", ".lever.co")):
            return "ats_or_job_link"
        if value in {"techcrunch.com", "forbes.com", "prnewswire.com", "medium.com", "crunchbase.com"}:
            return "news_article"
        return "blocked_platform"
    if "/jobs/" in lowered or "apply" in lowered:
        return "ats_or_job_link"
    if "news" in context.lower() or "launch" in lowered:
        return "news_article"
    if not _allowed_profile_domain(value):
        return "blocked_platform"
    return None


def _allowed_profile_domain(domain: str) -> bool:
    value = domain.lower()
    if not is_allowed_company_domain(value) or is_platform_or_shared_domain(value):
        return False
    return not any(value == blocked or value.endswith(f".{blocked}") for blocked in BLOCKED_PROFILE_DOMAINS)


def _text_domain_matches_href(text: str, domain: str) -> bool:
    cleaned = (text or "").strip().lower()
    if not URLISH_RE.match(cleaned):
        return False
    displayed = normalize_domain_proposal(cleaned)
    return displayed == domain or displayed == _root_domain(domain)


def _top_profile_anchor_limit(anchors: list[AnchorInfo]) -> int:
    section_markers = {"founder", "founders", "active founders", "company launches", "news", "jobs"}
    marker_indexes = [
        anchor.index
        for anchor in anchors
        if anchor.text.strip().lower() in section_markers and anchor.index > 2
    ]
    return min(marker_indexes) if marker_indexes else min(len(anchors), 30)


def _weak_external_context(anchor: AnchorInfo) -> bool:
    lowered = f"{anchor.text} {anchor.href} {anchor.context}".lower()
    return any(
        marker in lowered
        for marker in [
            "founder",
            "news",
            "launch",
            "docs.",
            "documentation",
            "blog",
            "jobs",
            "careers",
        ]
    )


def _canonical_company_url(url: str, domain: str, root_domain: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    scheme = parsed.scheme if parsed.scheme in {"http", "https"} else "https"
    if domain != root_domain:
        return f"https://{root_domain}"
    path = parsed.path.rstrip("/")
    if path and path != "/":
        return f"{scheme}://{root_domain}{path}"
    return f"{scheme}://{root_domain}"


def _root_domain(domain: str) -> str:
    value = domain.lower()
    if value.startswith("www."):
        value = value[4:]
    parts = value.split(".")
    if len(parts) <= 2:
        return value
    return ".".join(parts[-2:])


def _is_root_url(url: str, root_domain: str) -> bool:
    parsed = urlparse(url)
    return normalize_domain(parsed.hostname or "") == root_domain and parsed.path in {"", "/"}


def _context_hint(link: Tag) -> str:
    parts: list[str] = []
    for parent in link.parents:
        if not isinstance(parent, Tag):
            continue
        label = parent.get("aria-label")
        classes = parent.get("class")
        element_id = parent.get("id")
        role = parent.get("role")
        if label:
            parts.append(str(label))
        if classes:
            parts.extend(str(item) for item in classes)
        if element_id:
            parts.append(str(element_id))
        if role:
            parts.append(str(role))
        if parent.name in {"header", "nav", "main", "section", "footer"}:
            parts.append(parent.name)
        if len(parts) >= 8:
            break
    return " ".join(parts[:8])


def _global_chrome_reason(
    link: Tag, text: str, domain: str | None
) -> str | None:
    if GLOBAL_NAV_TEXT_RE.fullmatch((text or "").strip()):
        return "yc_global_navigation"
    if domain and (
        domain in {"startupschool.org", "startupschool.com", "workatastartup.com"}
        or domain == "ycombinator.com"
        or domain.endswith(".ycombinator.com")
    ):
        return "yc_ecosystem_link"
    for parent in link.parents:
        if not isinstance(parent, Tag):
            continue
        markers = " ".join(
            [
                parent.name or "",
                str(parent.get("id") or ""),
                " ".join(str(item) for item in (parent.get("class") or [])),
                str(parent.get("aria-label") or ""),
                str(parent.get("role") or ""),
            ]
        ).lower()
        if parent.name == "footer" or any(
            marker in markers
            for marker in (
                "global-nav",
                "global_nav",
                "site-nav",
                "site_nav",
                "navbar",
                "navigation-menu",
                "promo-banner",
                "announcement-banner",
                "legal-links",
                "ecosystem-links",
                "site-footer",
                "global-footer",
            )
        ):
            return "yc_global_navigation"
    return None


def _is_company_content_anchor(link: Tag) -> bool:
    for parent in link.parents:
        if not isinstance(parent, Tag):
            continue
        markers = " ".join(
            [
                parent.name or "",
                str(parent.get("id") or ""),
                " ".join(str(item) for item in (parent.get("class") or [])),
                str(parent.get("aria-label") or ""),
            ]
        ).lower()
        if parent.name in {"footer", "nav"} or any(
            marker in markers
            for marker in (
                "founder",
                "news",
                "launch",
                "jobs",
                "job-list",
                "social",
                "global-nav",
                "site-nav",
                "navbar",
                "promo-banner",
                "legal",
                "ecosystem",
                "footer",
            )
        ):
            return False
    # Small parser fixtures and older YC markup may not expose a main element.
    return True


def _is_company_header_context(context: str) -> bool:
    lowered = context.lower()
    return "company-header" in lowered or "company_header" in lowered or "header" in lowered


def _candidate_evidence(candidate: YCWebsiteCandidate) -> dict[str, Any]:
    return {
        "extraction_strategy": candidate.source,
        "anchor_text": candidate.anchor_text,
        "original_href": candidate.original_href,
        "normalized_url": candidate.url,
        "normalized_domain": candidate.root_domain,
        "observed_domain": candidate.domain,
        "dom_context": candidate.context,
        "confidence": candidate.confidence,
    }


def _anchor_evidence(anchor: AnchorInfo) -> dict[str, Any]:
    return {
        "anchor_text": anchor.text,
        "original_href": anchor.href,
        "normalized_url": anchor.normalized_url,
        "normalized_domain": anchor.domain,
        "dom_context": anchor.context,
        "rejection_reason": anchor.rejected_reason,
    }


def _text_after_marker(text: str, marker: str) -> str | None:
    parts = text.split(marker, 1)
    if len(parts) != 2:
        return None
    value = _clean_text(parts[1]).split("  ", 1)[0].strip(" :")
    return value[:120] or None


def _clean_text(value: str | None) -> str | None:
    cleaned = " ".join(unescape(value or "").split())
    return cleaned or None
