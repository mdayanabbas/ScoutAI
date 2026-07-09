import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.enrichment.domain_extractor import clean_enrichment_text, extract_urls_from_text
from app.models.discovery_candidate import DiscoveryCandidate
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryDecision, DiscoverySource, RemoteType, RoleCategory


@dataclass(frozen=True)
class ParsedHackerNewsJob:
    title: str
    description: str | None
    location: str | None
    remote_type: RemoteType
    role_category: RoleCategory
    job_url: str


def is_hacker_news_hiring_candidate(candidate: DiscoveryCandidate) -> bool:
    if candidate.source != DiscoverySource.HACKER_NEWS:
        return False
    payload = candidate.raw_payload or {}
    if payload.get("feed") == "jobs" or payload.get("type") == "job":
        return True
    return any(evidence.evidence_type == "hiring_post" for evidence in candidate.evidence)


def parse_hacker_news_job(candidate: DiscoveryCandidate) -> ParsedHackerNewsJob:
    description = build_job_description(candidate)
    title = extract_job_title(candidate)
    return ParsedHackerNewsJob(
        title=title,
        description=description,
        location=extract_job_location(candidate),
        remote_type=extract_remote_signal(candidate),
        role_category=role_category_for_title(title),
        job_url=select_job_url(candidate),
    )


def extract_job_title(candidate: DiscoveryCandidate) -> str:
    title = _raw_title(candidate)
    if not title:
        return "Open Roles"
    cleaned = re.sub(r"\([^)]*\)", "", title)
    match = re.search(r"\bis hiring\b(?P<rest>.*)$", cleaned, re.IGNORECASE)
    if not match:
        return "Open Roles"
    rest = match.group("rest").strip(" -:,.")
    rest = re.sub(r"^(a|an|for our|for)\s+", "", rest, flags=re.IGNORECASE)
    if re.match(r"^in\s+", rest, re.IGNORECASE):
        return "Open Roles"
    rest = re.split(r"\s+\bin\b\s+", rest, maxsplit=1, flags=re.IGNORECASE)[0]
    rest = re.split(r"\s+\bto\b\s+", rest, maxsplit=1, flags=re.IGNORECASE)[0]
    rest = rest.strip(" -:,.")
    if not rest:
        return "Open Roles"
    if re.search(r"\bgtm team\b", rest, re.IGNORECASE):
        return "GTM Team Roles"
    return rest


def extract_job_location(candidate: DiscoveryCandidate) -> str | None:
    title = _raw_title(candidate) or ""
    match = re.search(r"\bis hiring(?:.*?)\bin\s+([^|()]+)$", title, re.IGNORECASE)
    if match:
        location = _clean_location(match.group(1))
        if location and not re.search(r"\b(remote|hybrid|office|onsite|on-site)\b", location, re.IGNORECASE):
            return location
    description = build_job_description(candidate) or ""
    match = re.search(r"(?im)^\s*Location:\s*(.+)$", description)
    if match:
        return _clean_location(match.group(1))
    return None


def extract_remote_signal(candidate: DiscoveryCandidate) -> RemoteType:
    text = f"{_raw_title(candidate) or ''}\n{build_job_description(candidate) or ''}".lower()
    negative_remote = "not a good fit" in text and "prefer" in text and "remote" in text
    if re.search(r"\b(on-site|onsite|in-office)\b", text):
        if "hybrid" in text:
            return RemoteType.HYBRID
        return RemoteType.ONSITE
    if "hybrid" in text:
        return RemoteType.HYBRID
    if not negative_remote and re.search(r"\b(remote|remote-first|fully remote)\b", text):
        return RemoteType.REMOTE_WORLDWIDE
    return RemoteType.UNKNOWN


def extract_employment_type(candidate: DiscoveryCandidate) -> str | None:
    text = build_job_description(candidate) or ""
    if re.search(r"\bfull[- ]time\b", text, re.IGNORECASE):
        return "full_time"
    if re.search(r"\bpart[- ]time\b", text, re.IGNORECASE):
        return "part_time"
    if re.search(r"\bcontract\b", text, re.IGNORECASE):
        return "contract"
    if re.search(r"\binternship\b", text, re.IGNORECASE):
        return "internship"
    if re.search(r"\btemporary\b", text, re.IGNORECASE):
        return "temporary"
    return None


def extract_salary_text(candidate: DiscoveryCandidate) -> str | None:
    text = build_job_description(candidate) or ""
    match = re.search(r"([$€£][^\n]{0,80}?(?:equity|k|K|000))", text)
    return match.group(1).strip() if match else None


def select_job_url(candidate: DiscoveryCandidate) -> str:
    payload = candidate.raw_payload or {}
    if _safe_url(payload.get("url")):
        return payload["url"]
    description = build_job_description(candidate) or ""
    for url in extract_urls_from_text(description):
        if _safe_url(url):
            return url
    item_id = payload.get("id") or _source_item_id(candidate.source_identifier)
    if item_id:
        return f"https://news.ycombinator.com/item?id={item_id}"
    return f"https://news.ycombinator.com/item?id={candidate.source_identifier}"


def build_job_description(candidate: DiscoveryCandidate) -> str | None:
    for value in [
        candidate.normalized_description,
        candidate.raw_description,
        (candidate.raw_payload or {}).get("text"),
        _raw_title(candidate),
    ]:
        cleaned = clean_enrichment_text(value)
        if cleaned:
            return cleaned
    return None


def _raw_title(candidate: DiscoveryCandidate) -> str | None:
    payload = candidate.raw_payload or {}
    title = payload.get("title")
    return title if isinstance(title, str) else candidate.raw_name


def _source_item_id(source_identifier: str) -> str | None:
    return source_identifier.split(":", 1)[1] if source_identifier.startswith("hn:") else None


def _safe_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password


def _clean_location(value: str) -> str | None:
    location = value.strip(" .,:;-")
    return location or None


def role_category_for_title(title: str) -> RoleCategory:
    value = title.lower()
    if "backend" in value:
        return RoleCategory.BACKEND_ENGINEER
    if "frontend" in value:
        return RoleCategory.FRONTEND_ENGINEER
    if "full stack" in value or "full-stack" in value:
        return RoleCategory.FULL_STACK_ENGINEER
    if "ml" in value or "machine learning" in value:
        return RoleCategory.ML_ENGINEER
    if "data" in value:
        return RoleCategory.DATA_ENGINEER
    if "devops" in value:
        return RoleCategory.DEVOPS_ENGINEER
    if "engineer" in value or value == "swe":
        return RoleCategory.SOFTWARE_ENGINEER
    return RoleCategory.OTHER
