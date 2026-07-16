from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


MIN_TIMESTAMP = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()
MAX_TIMESTAMP = datetime(2100, 1, 1, tzinfo=timezone.utc).timestamp()
MILLISECOND_THRESHOLD = 10_000_000_000


@dataclass(frozen=True)
class HimalayasTimestampParseResult:
    value: datetime | None
    error: str | None = None


def parse_himalayas_timestamp(value: Any, *, allow_null: bool = True) -> HimalayasTimestampParseResult:
    if value is None:
        return HimalayasTimestampParseResult(None, None if allow_null else "timestamp_required")
    if isinstance(value, datetime):
        parsed = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return _bounded_timestamp(parsed)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return HimalayasTimestampParseResult(None, None if allow_null else "timestamp_required")
        if stripped.isdigit() and len(stripped) in {10, 13}:
            return _timestamp_from_number(int(stripped))
        try:
            parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError:
            return HimalayasTimestampParseResult(None, "timestamp_invalid")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return _bounded_timestamp(parsed.astimezone(timezone.utc))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < 0:
            return HimalayasTimestampParseResult(None, "timestamp_negative")
        return _timestamp_from_number(value)
    return HimalayasTimestampParseResult(None, "timestamp_invalid_type")


def _timestamp_from_number(value: int | float) -> HimalayasTimestampParseResult:
    seconds = float(value) / 1000 if value > MILLISECOND_THRESHOLD else float(value)
    try:
        parsed = datetime.fromtimestamp(seconds, timezone.utc)
    except (OverflowError, OSError, ValueError):
        return HimalayasTimestampParseResult(None, "timestamp_out_of_range")
    return _bounded_timestamp(parsed)


def _bounded_timestamp(value: datetime) -> HimalayasTimestampParseResult:
    seconds = value.timestamp()
    if seconds < MIN_TIMESTAMP or seconds > MAX_TIMESTAMP:
        return HimalayasTimestampParseResult(None, "timestamp_out_of_range")
    return HimalayasTimestampParseResult(value)


class HimalayasLocationRestriction(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    alpha2: str | None = None
    name: str | None = None
    slug: str | None = None


class HimalayasJobPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    title: str | None = None
    excerpt: str | None = None
    company_name: str | None = Field(default=None, alias="companyName")
    company_slug: str | None = Field(default=None, alias="companySlug")
    company_logo: str | None = Field(default=None, alias="companyLogo")
    employment_type: str | None = Field(default=None, alias="employmentType")
    minimum_salary: float | None = Field(default=None, alias="minSalary")
    maximum_salary: float | None = Field(default=None, alias="maxSalary")
    salary_period: str | None = Field(default="annual", alias="salaryPeriod")
    seniority: list[str] = Field(default_factory=list)
    currency: str | None = None
    location_restrictions: list[HimalayasLocationRestriction] | None = Field(default=None, alias="locationRestrictions")
    timezone_restrictions: list[str] = Field(default_factory=list, alias="timezoneRestrictions")
    categories: list[str] = Field(default_factory=list)
    parent_categories: list[str] = Field(default_factory=list, alias="parentCategories")
    description_html: str | None = Field(default=None, alias="description")
    published_at: datetime | None = Field(default=None, alias="pubDate")
    expiry_at: datetime | None = Field(default=None, alias="expiryDate")
    published_at_parse_error: str | None = None
    expiry_at_parse_error: str | None = None
    application_link: str | None = Field(default=None, alias="applicationLink")
    guid: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "timezoneRestrictions" not in data and "timezoneRestriction" in data:
            data["timezoneRestrictions"] = data.get("timezoneRestriction")
        if "categories" not in data and "category" in data:
            data["categories"] = data.get("category")
        if not data.get("salaryPeriod"):
            data["salaryPeriod"] = "annual"
        pub = parse_himalayas_timestamp(data.get("pubDate"))
        data["pubDate"] = pub.value
        data["published_at_parse_error"] = pub.error
        expiry = parse_himalayas_timestamp(data.get("expiryDate"))
        data["expiryDate"] = expiry.value
        data["expiry_at_parse_error"] = expiry.error
        return data

    @field_validator("categories", "parent_categories", "timezone_restrictions", mode="before")
    @classmethod
    def normalize_string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        return _dedupe_strings(value)

    @field_validator("seniority", mode="before")
    @classmethod
    def normalize_seniority(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        return _dedupe_strings(value)


class HimalayasJobsEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    comments: str | None = None
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    updated_at_parse_error: str | None = None
    offset: int = 0
    limit: int = 0
    total_count: int = Field(default=0, alias="totalCount")
    jobs_raw: list[Any] = Field(default_factory=list, alias="jobs")

    @model_validator(mode="before")
    @classmethod
    def normalize_updated_at(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        parsed = parse_himalayas_timestamp(data.get("updatedAt"), allow_null=False)
        data["updatedAt"] = parsed.value
        data["updated_at_parse_error"] = parsed.error
        return data


class HimalayasSearchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    comments: str | None = None
    updated_at: datetime | None = None
    offset: int = 0
    limit: int = 0
    total_count: int = 0
    jobs: list[HimalayasJobPayload] = Field(default_factory=list)
    malformed_records: int = 0
    validation_failures: list[dict[str, Any]] = Field(default_factory=list)
    status_code: int | None = None
    reason: str | None = None
    error_code: str | None = None
    error_summary: str | None = None
    schema_diagnostics: dict[str, Any] | None = None
    response_size: int | None = None


class HimalayasSearchRequest(BaseModel):
    query: str
    country: str | None = None
    worldwide: bool | None = None
    exclude_worldwide: bool | None = None
    seniority: list[str] | None = None
    employment_types: list[str] | None = None
    sort: str = "recent"
    page: int = 1


def parse_himalayas_jobs_response(
    payload: Any,
    *,
    status_code: int | None = None,
    response_size: int | None = None,
    content_type: str | None = None,
    provider_request_id: str | None = None,
) -> HimalayasSearchResponse:
    if not isinstance(payload, dict):
        return _schema_error(
            payload,
            status_code=status_code,
            response_size=response_size,
            content_type=content_type,
            provider_request_id=provider_request_id,
            validation_paths=[],
        )
    if "jobs" not in payload or not isinstance(payload.get("jobs"), list) or not _usable_int(payload.get("totalCount")):
        return _schema_error(
            payload,
            status_code=status_code,
            response_size=response_size,
            content_type=content_type,
            provider_request_id=provider_request_id,
            validation_paths=["jobs" if not isinstance(payload.get("jobs"), list) else "totalCount"],
        )
    try:
        envelope = HimalayasJobsEnvelope.model_validate(payload)
    except ValidationError as exc:
        return _schema_error(
            payload,
            status_code=status_code,
            response_size=response_size,
            content_type=content_type,
            provider_request_id=provider_request_id,
            validation_paths=_validation_paths(exc),
        )

    valid_jobs: list[HimalayasJobPayload] = []
    failures: list[dict[str, Any]] = []
    for index, raw_job in enumerate(envelope.jobs_raw):
        if not isinstance(raw_job, dict):
            failures.append({"index": index, "paths": [f"jobs.{index}"], "error": "job_not_object"})
            continue
        try:
            valid_jobs.append(HimalayasJobPayload.model_validate(raw_job))
        except ValidationError as exc:
            failures.append({"index": index, "paths": [f"jobs.{index}.{path}" for path in _validation_paths(exc)[:5]], "error": "job_validation_failed"})
    return HimalayasSearchResponse(
        comments=envelope.comments,
        updated_at=envelope.updated_at,
        offset=envelope.offset,
        limit=envelope.limit,
        total_count=envelope.total_count,
        jobs=valid_jobs,
        malformed_records=len(failures),
        validation_failures=failures[:10],
        status_code=status_code,
        response_size=response_size,
    )


def schema_diagnostics_for_payload(
    payload: Any,
    *,
    status_code: int | None,
    response_size: int | None,
    content_type: str | None,
    provider_request_id: str | None,
    validation_paths: list[str],
) -> dict[str, Any]:
    if isinstance(payload, dict):
        keys = list(payload.keys())[:30]
        field_types = {key: type(value).__name__ for key, value in payload.items() if key in keys}
        jobs_type = type(payload.get("jobs")).__name__
    else:
        keys = []
        field_types = {"body": type(payload).__name__}
        jobs_type = "missing"
    diagnostics = {
        "status_code": status_code,
        "content_type": content_type,
        "top_level_keys": keys,
        "field_types": field_types,
        "jobs_value_type": jobs_type,
        "validation_paths": validation_paths[:10],
        "response_size": response_size,
    }
    if provider_request_id:
        diagnostics["provider_request_id"] = provider_request_id
    return diagnostics


def _schema_error(
    payload: Any,
    *,
    status_code: int | None,
    response_size: int | None,
    content_type: str | None,
    provider_request_id: str | None,
    validation_paths: list[str],
) -> HimalayasSearchResponse:
    diagnostics = schema_diagnostics_for_payload(
        payload,
        status_code=status_code,
        response_size=response_size,
        content_type=content_type,
        provider_request_id=provider_request_id,
        validation_paths=validation_paths,
    )
    return HimalayasSearchResponse(
        status_code=status_code,
        response_size=response_size,
        reason="himalayas_unexpected_schema",
        error_code="himalayas_unexpected_schema",
        error_summary="Invalid Himalayas response envelope",
        schema_diagnostics=diagnostics,
    )


def _dedupe_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _usable_int(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def _validation_paths(exc: ValidationError) -> list[str]:
    paths = []
    for error in exc.errors()[:10]:
        loc = ".".join(str(part) for part in error.get("loc", ()))
        paths.append(loc or "response")
    return paths
