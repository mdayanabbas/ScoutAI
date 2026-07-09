from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.enrichment.domain_extractor import clean_enrichment_text


@dataclass(frozen=True)
class AshbyPublicJob:
    title: str
    location: str | None
    secondary_locations: tuple[str, ...]
    department: str | None
    team: str | None
    is_listed: bool
    is_remote: bool | None
    workplace_type: str | None
    description_plain: str | None
    description_html: str | None
    published_at: datetime | None
    employment_type: str | None
    job_url: str | None
    apply_url: str | None
    compensation_summary: str | None
    raw_posting_id: str | None

    def focused_metadata(self) -> dict[str, Any]:
        return {
            "posting_id": self.raw_posting_id,
            "location": self.location,
            "secondary_locations": list(self.secondary_locations),
            "department": self.department,
            "team": self.team,
            "is_remote": self.is_remote,
            "workplace_type": self.workplace_type,
            "employment_type": self.employment_type,
            "job_url": self.job_url,
            "apply_url": self.apply_url,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "compensation_summary": self.compensation_summary,
            "description_plain": (self.description_plain or "")[:10_000] or None,
        }


def parse_ashby_job_board(payload: Any) -> list[AshbyPublicJob] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        return None
    jobs: list[AshbyPublicJob] = []
    for item in payload["jobs"]:
        parsed = parse_ashby_public_job(item)
        if parsed is not None and parsed.is_listed:
            jobs.append(parsed)
    return jobs


def parse_ashby_public_job(item: Any) -> AshbyPublicJob | None:
    if not isinstance(item, dict):
        return None
    title = _string(item.get("title"))
    if not title:
        return None
    job_url = _safe_url(item.get("jobUrl"))
    apply_url = _safe_url(item.get("applyUrl"))
    return AshbyPublicJob(
        title=title,
        location=_location(item.get("location")),
        secondary_locations=_secondary_locations(item.get("secondaryLocations")),
        department=_named_value(item.get("department")),
        team=_named_value(item.get("team")),
        is_listed=item.get("isListed") is not False,
        is_remote=item.get("isRemote") if isinstance(item.get("isRemote"), bool) else None,
        workplace_type=_string(item.get("workplaceType")),
        description_plain=_clean_optional(item.get("descriptionPlain")),
        description_html=_string(item.get("descriptionHtml")),
        published_at=_datetime(item.get("publishedAt")),
        employment_type=_string(item.get("employmentType")),
        job_url=job_url,
        apply_url=apply_url,
        compensation_summary=_compensation(item.get("compensation")),
        raw_posting_id=_posting_id(item, job_url, apply_url),
    )


def _string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _clean_optional(value: Any) -> str | None:
    cleaned = clean_enrichment_text(value) if isinstance(value, str) else ""
    return cleaned or None


def _safe_url(value: Any) -> str | None:
    text = _string(value)
    if not text:
        return None
    parsed = urlparse(text)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        return None
    return text


def _named_value(value: Any) -> str | None:
    if isinstance(value, dict):
        return _string(value.get("name"))
    return _string(value)


def _location(value: Any) -> str | None:
    if isinstance(value, dict):
        return _string(value.get("name") or value.get("location"))
    return _string(value)


def _secondary_locations(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        location
        for item in value
        if (location := _location(item)) is not None
    )


def _datetime(value: Any) -> datetime | None:
    text = _string(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _compensation(value: Any) -> str | None:
    if isinstance(value, str):
        return _string(value)
    if not isinstance(value, dict):
        return None
    for key in ("compensationSummary", "summary", "scrapeableCompensationSalarySummary"):
        if summary := _string(value.get(key)):
            return summary
    return None


def _posting_id(
    item: dict[str, Any], job_url: str | None, apply_url: str | None
) -> str | None:
    for value in (item.get("id"), item.get("jobPostingId")):
        if text := _string(value):
            return text
    for value in (job_url, apply_url):
        if not value:
            continue
        parts = [part for part in urlparse(value).path.split("/") if part]
        if len(parts) >= 2:
            return parts[1]
    return None
