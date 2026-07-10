import json
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

LEGAL_SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|llc|ltd|limited|gmbh|corp|corporation|company|co)\b\.?",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class HomepageMetadata:
    url: str
    title: str | None = None
    og_site_name: str | None = None
    og_title: str | None = None
    organization_names: tuple[str, ...] = ()
    canonical_url: str | None = None
    header_text: str | None = None
    status_code: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class CompanyIdentityCheckResult:
    matched: bool
    confidence: float
    matched_signals: tuple[str, ...] = ()
    conflicting_signals: tuple[str, ...] = ()
    reason: str | None = None


def check_company_identity(
    company_name: str,
    metadata: HomepageMetadata | None,
) -> CompanyIdentityCheckResult:
    if metadata is None:
        return CompanyIdentityCheckResult(False, 0.0, reason="homepage_metadata_missing")
    expected = _normalize_name(company_name)
    if not expected:
        return CompanyIdentityCheckResult(False, 0.0, reason="company_name_missing")

    matched: list[str] = []
    conflicts: list[str] = []
    fields = {
        "title": metadata.title,
        "og_site_name": metadata.og_site_name,
        "og_title": metadata.og_title,
        "header_text": metadata.header_text,
    }
    for label, value in fields.items():
        signal = _classify(expected, value)
        if signal == "match":
            matched.append(label)
        elif signal == "conflict":
            conflicts.append(label)
    for name in metadata.organization_names:
        signal = _classify(expected, name)
        if signal == "match":
            matched.append("json_ld_organization_name")
        elif signal == "conflict":
            conflicts.append("json_ld_organization_name")

    if conflicts and not matched:
        return CompanyIdentityCheckResult(
            False,
            0.0,
            tuple(matched),
            tuple(conflicts),
            "homepage_identity_mismatch",
        )
    if len(matched) >= 2:
        return CompanyIdentityCheckResult(
            True, 0.95, tuple(matched), tuple(conflicts), "homepage_identity_match"
        )
    if matched:
        confidence = 0.9 if not conflicts else 0.75
        return CompanyIdentityCheckResult(
            confidence >= 0.85,
            confidence,
            tuple(matched),
            tuple(conflicts),
            "homepage_identity_match" if confidence >= 0.85 else "homepage_identity_weak",
        )
    return CompanyIdentityCheckResult(
        False, 0.0, tuple(), tuple(conflicts), "homepage_identity_mismatch"
    )


def extract_homepage_metadata(
    html: str,
    url: str,
    *,
    status_code: int | None = None,
) -> HomepageMetadata:
    soup = BeautifulSoup(html[:200_000], "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    headers = [
        node.get_text(" ", strip=True)
        for node in soup.find_all(["h1", "h2"], limit=4)
        if node.get_text(" ", strip=True)
    ]
    organization_names: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}, limit=5):
        text = script.string or script.get_text()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        organization_names.extend(_json_ld_organization_names(payload))

    return HomepageMetadata(
        url=url,
        title=title[:200] if title else None,
        og_site_name=_meta_content(soup, "og:site_name"),
        og_title=_meta_content(soup, "og:title"),
        organization_names=tuple(dict.fromkeys(name[:160] for name in organization_names)),
        canonical_url=_canonical_url(soup),
        header_text=" ".join(headers)[:300] if headers else None,
        status_code=status_code,
    )


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    node = soup.find("meta", attrs={"property": property_name})
    value = node.get("content") if node else None
    return value.strip()[:200] if isinstance(value, str) and value.strip() else None


def _canonical_url(soup: BeautifulSoup) -> str | None:
    node = soup.find("link", attrs={"rel": "canonical"})
    value = node.get("href") if node else None
    return value.strip()[:500] if isinstance(value, str) and value.strip() else None


def _json_ld_organization_names(payload: Any) -> list[str]:
    items = payload if isinstance(payload, list) else [payload]
    names: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        graph = item.get("@graph")
        if isinstance(graph, list):
            names.extend(_json_ld_organization_names(graph))
        item_type = item.get("@type")
        types = item_type if isinstance(item_type, list) else [item_type]
        if any(value in {"Organization", "Corporation", "LocalBusiness"} for value in types):
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names


def _classify(expected: str, value: str | None) -> str | None:
    normalized = _normalize_name(value)
    if not normalized:
        return None
    if normalized == expected:
        return "match"
    if normalized.startswith(f"{expected} ") or normalized.startswith(f"{expected} |"):
        return "match"
    if normalized.startswith(f"{expected} -") or normalized.startswith(f"{expected} "):
        return "match"
    expected_tokens = set(TOKEN_RE.findall(expected))
    value_tokens = set(TOKEN_RE.findall(normalized))
    if expected_tokens and expected_tokens.issubset(value_tokens):
        extra_tokens = value_tokens - expected_tokens
        return "match" if len(extra_tokens) <= 8 else None
    if expected_tokens & value_tokens:
        return None
    return "conflict"


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    cleaned = LEGAL_SUFFIX_RE.sub(" ", value)
    cleaned = re.sub(r"[\W_]+", " ", cleaned.lower())
    return re.sub(r"\s+", " ", cleaned).strip()
