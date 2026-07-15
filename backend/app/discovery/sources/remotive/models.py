from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


@dataclass(frozen=True)
class RemotiveMalformedJob:
    index: int
    source_id: str | None = None
    validation_paths: list[str] = field(default_factory=list)
    reason: str = "malformed_job"


class RemotiveJobPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    source_id: str | None = Field(default=None, alias="id")
    url: str | None = None
    title: str | None = None
    company_name: str | None = None
    company_logo: str | None = None
    category: str | None = None
    job_type: str | None = None
    publication_date: datetime | None = None
    publication_date_parse_error: str | None = None
    candidate_required_location: str | None = None
    salary_text: str | None = Field(default=None, alias="salary")
    description_html: str | None = Field(default=None, alias="description")

    @model_validator(mode="before")
    @classmethod
    def normalize_external_values(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "id" in data and data.get("id") is not None:
            data["id"] = str(data.get("id"))
        parsed, error = parse_remotive_datetime(data.get("publication_date"))
        data["publication_date"] = parsed
        data["publication_date_parse_error"] = error
        return data

    @field_validator(
        "source_id",
        "url",
        "title",
        "company_name",
        "company_logo",
        "category",
        "job_type",
        "candidate_required_location",
        "salary_text",
        mode="before",
    )
    @classmethod
    def normalize_text_field(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class RemotiveJobsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    legal_notice: str | None = Field(default=None, alias="0-legal-notice")
    job_count: int = Field(default=0, alias="job-count")
    jobs: list[RemotiveJobPayload] = Field(default_factory=list)
    malformed_jobs: list[RemotiveMalformedJob] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status_code: int | None = None
    reason: str | None = None
    error_code: str | None = None
    response_size: int | None = None


def parse_remotive_jobs_response(
    payload: Any,
    *,
    status_code: int | None = None,
    response_size: int | None = None,
) -> RemotiveJobsResponse:
    if not isinstance(payload, dict):
        return _envelope_error("remotive_invalid_envelope", status_code=status_code, response_size=response_size)
    if "jobs" not in payload or not isinstance(payload.get("jobs"), list):
        return _envelope_error("remotive_invalid_envelope", status_code=status_code, response_size=response_size)
    job_count = _safe_int(payload.get("job-count"))
    if job_count is None:
        return _envelope_error("remotive_invalid_envelope", status_code=status_code, response_size=response_size)

    jobs: list[RemotiveJobPayload] = []
    malformed: list[RemotiveMalformedJob] = []
    warnings: list[str] = []
    for index, raw_job in enumerate(payload.get("jobs") or []):
        if not isinstance(raw_job, dict):
            malformed.append(RemotiveMalformedJob(index=index, reason="job_not_object"))
            continue
        try:
            job = RemotiveJobPayload.model_validate(raw_job)
        except ValidationError as exc:
            malformed.append(RemotiveMalformedJob(index=index, validation_paths=_paths(exc), reason="job_validation_failed"))
            continue
        if job.publication_date_parse_error:
            warnings.append(f"jobs.{index}.publication_date:{job.publication_date_parse_error}")
        if not job.title:
            malformed.append(RemotiveMalformedJob(index=index, source_id=job.source_id, validation_paths=["title"], reason="missing_title"))
            continue
        jobs.append(job)
    return RemotiveJobsResponse(
        legal_notice=payload.get("0-legal-notice"),
        job_count=job_count,
        jobs=jobs,
        malformed_jobs=malformed,
        warnings=warnings[:20],
        status_code=status_code,
        response_size=response_size,
    )


def parse_remotive_datetime(value: Any) -> tuple[datetime | None, str | None]:
    if value is None or str(value).strip() == "":
        return None, None
    if isinstance(value, datetime):
        return (value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)), None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None, "invalid_publication_date"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc), None


def _envelope_error(code: str, *, status_code: int | None, response_size: int | None) -> RemotiveJobsResponse:
    return RemotiveJobsResponse(
        status_code=status_code,
        reason=code,
        error_code=code,
        response_size=response_size,
    )


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _paths(exc: ValidationError) -> list[str]:
    return [".".join(str(part) for part in err.get("loc", ())) or "job" for err in exc.errors()[:5]]
