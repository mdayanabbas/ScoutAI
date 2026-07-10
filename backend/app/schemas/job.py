from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.enums import JobStatus, RemoteType, RoleCategory


class JobBase(BaseModel):
    discovery_candidate_id: str | None = None
    title: str
    role_category: RoleCategory | None = RoleCategory.OTHER
    description: str | None = None
    location: str | None = None
    remote_type: RemoteType | None = RemoteType.UNKNOWN
    experience_min: int | None = Field(default=None, ge=0)
    experience_max: int | None = Field(default=None, ge=0)
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    job_url: str
    source_platform: str | None = None
    status: JobStatus = JobStatus.ACTIVE
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    seniority: str | None = None
    employment_type: str | None = None
    apply_url: str | None = None
    published_at: datetime | None = None
    last_verified_at: datetime | None = None
    salary_text: str | None = None
    equity_mentioned: bool | None = None
    visa_sponsorship: str | None = None
    work_authorization: str | None = None
    required_skills_json: list[str] | None = None
    preferred_skills_json: list[str] | None = None
    technologies_json: list[str] | None = None
    enrichment_status: str = "not_enriched"
    enrichment_confidence: float | None = None
    enriched_at: datetime | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if (
            self.experience_min is not None
            and self.experience_max is not None
            and self.experience_min > self.experience_max
        ):
            raise ValueError("experience_min must be <= experience_max")
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must be <= salary_max")
        return self


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    discovery_candidate_id: str | None = None
    title: str | None = None
    role_category: RoleCategory | None = None
    description: str | None = None
    location: str | None = None
    remote_type: RemoteType | None = None
    experience_min: int | None = Field(default=None, ge=0)
    experience_max: int | None = Field(default=None, ge=0)
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    job_url: str | None = None
    source_platform: str | None = None
    status: JobStatus | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    seniority: str | None = None
    employment_type: str | None = None
    apply_url: str | None = None
    published_at: datetime | None = None
    last_verified_at: datetime | None = None
    salary_text: str | None = None
    equity_mentioned: bool | None = None
    visa_sponsorship: str | None = None
    work_authorization: str | None = None
    required_skills_json: list[str] | None = None
    preferred_skills_json: list[str] | None = None
    technologies_json: list[str] | None = None
    enrichment_status: str | None = None
    enrichment_confidence: float | None = None
    enriched_at: datetime | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if (
            self.experience_min is not None
            and self.experience_max is not None
            and self.experience_min > self.experience_max
        ):
            raise ValueError("experience_min must be <= experience_max")
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must be <= salary_max")
        return self


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    company_name: str | None = None
    company_website_url: str | None = None
    normalized_title: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_company_fields(cls, value: Any) -> Any:
        return _map_company_fields(value)


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    company_name: str | None = None
    company_website_url: str | None = None
    discovery_candidate_id: str | None = None
    title: str
    normalized_title: str | None = None
    role_category: RoleCategory | None = None
    location: str | None = None
    remote_type: RemoteType | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    job_url: str | None = None
    source_platform: str | None = None
    status: JobStatus
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    seniority: str | None = None
    employment_type: str | None = None
    apply_url: str | None = None
    published_at: datetime | None = None
    last_verified_at: datetime | None = None
    salary_text: str | None = None
    equity_mentioned: bool | None = None
    visa_sponsorship: str | None = None
    work_authorization: str | None = None
    required_skills_json: list[str] | None = None
    preferred_skills_json: list[str] | None = None
    technologies_json: list[str] | None = None
    enrichment_status: str = "not_enriched"
    enrichment_confidence: float | None = None
    enriched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_company_fields(cls, value: Any) -> Any:
        return _map_company_fields(value)


def _map_company_fields(value: Any) -> Any:
    if isinstance(value, dict):
        if "company" in value and value["company"] is not None:
            company = value["company"]
            if isinstance(company, dict):
                value.setdefault("company_name", company.get("name"))
                value.setdefault("company_website_url", company.get("website_url"))
        return value
    try:
        company = getattr(value, "company", None)
    except Exception:
        company = None
    if company is not None:
        return {
            "id": value.id,
            "company_id": value.company_id,
            "company_name": getattr(company, "name", None),
            "company_website_url": getattr(company, "website_url", None),
            "discovery_candidate_id": getattr(value, "discovery_candidate_id", None),
            "title": value.title,
            "normalized_title": value.normalized_title,
            "role_category": value.role_category,
            "description": getattr(value, "description", None),
            "location": value.location,
            "remote_type": value.remote_type,
            "experience_min": value.experience_min,
            "experience_max": value.experience_max,
            "salary_min": value.salary_min,
            "salary_max": value.salary_max,
            "salary_currency": value.salary_currency,
            "job_url": value.job_url,
            "source_platform": value.source_platform,
            "status": value.status,
            "first_seen_at": value.first_seen_at,
            "last_seen_at": value.last_seen_at,
            "seniority": getattr(value, "seniority", None),
            "employment_type": getattr(value, "employment_type", None),
            "apply_url": getattr(value, "apply_url", None),
            "published_at": getattr(value, "published_at", None),
            "last_verified_at": getattr(value, "last_verified_at", None),
            "salary_text": getattr(value, "salary_text", None),
            "equity_mentioned": getattr(value, "equity_mentioned", None),
            "visa_sponsorship": getattr(value, "visa_sponsorship", None),
            "work_authorization": getattr(value, "work_authorization", None),
            "required_skills_json": getattr(value, "required_skills_json", None),
            "preferred_skills_json": getattr(value, "preferred_skills_json", None),
            "technologies_json": getattr(value, "technologies_json", None),
            "enrichment_status": getattr(value, "enrichment_status", "not_enriched"),
            "enrichment_confidence": getattr(value, "enrichment_confidence", None),
            "enriched_at": getattr(value, "enriched_at", None),
            "created_at": value.created_at,
            "updated_at": value.updated_at,
        }
    return value


class JobEnrichmentAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    provider: str
    status: str
    reason: str | None = None
    error_message: str | None = None
    source_url: str | None = None
    extracted_data: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    field_confidence: dict[str, Any] | None = None
    started_at: datetime
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_json_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            if "extracted_data" not in value and "extracted_data_json" in value:
                value["extracted_data"] = value["extracted_data_json"]
            if "evidence" not in value and "evidence_json" in value:
                value["evidence"] = value["evidence_json"]
            if "field_confidence" not in value and "field_confidence_json" in value:
                value["field_confidence"] = value["field_confidence_json"]
            return value
        if hasattr(value, "extracted_data_json"):
            return {
                "id": value.id,
                "job_id": value.job_id,
                "provider": value.provider,
                "status": value.status,
                "reason": value.reason,
                "error_message": value.error_message,
                "source_url": value.source_url,
                "extracted_data": value.extracted_data_json,
                "evidence": value.evidence_json,
                "field_confidence": value.field_confidence_json,
                "started_at": value.started_at,
                "finished_at": value.finished_at,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        return value


class JobEnrichmentAttemptListRead(BaseModel):
    items: list[JobEnrichmentAttemptRead]
    total: int
    limit: int
    offset: int


class JobEnrichmentRunRead(BaseModel):
    job_id: str
    provider: str | None = None
    status: str
    reason: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    canonical_url: str | None = None
    fields_updated: dict[str, Any] = Field(default_factory=dict)
    fields_preserved: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    enrichment_confidence: float | None = None
    attempt: JobEnrichmentAttemptRead | None = None
    job: JobRead | None = None


class JobBatchEnrichmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int | None = Field(default=None, ge=1)
    job_ids: list[str] | None = None
    include_failed: bool = False
    force: bool = False

    @field_validator("job_ids")
    @classmethod
    def validate_job_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("job_ids must not be empty")
        from uuid import UUID

        for item in value:
            UUID(item)
        return value


class JobBatchEnrichmentItemRead(BaseModel):
    job_id: str
    company_name: str | None = None
    previous_title: str | None = None
    current_title: str | None = None
    provider: str | None = None
    status: str
    reason: str | None = None
    fields_updated: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    attempt_id: str | None = None
    enrichment_confidence: float | None = None


class JobBatchEnrichmentRead(BaseModel):
    jobs_examined: int
    jobs_enriched: int
    jobs_partially_enriched: int
    jobs_unresolved: int
    jobs_failed: int
    jobs_skipped: int
    jobs_missing: int
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    results: list[JobBatchEnrichmentItemRead]


class AshbyBoardExpansionCandidateRead(BaseModel):
    posting_id: str | None = None
    title: str | None = None
    canonical_job_url: str | None = None
    apply_url: str | None = None
    department: str | None = None
    team: str | None = None
    location: str | None = None
    employment_type: str | None = None
    match_score: float = 0.0
    matched_signals: list[str] = Field(default_factory=list)
    rejected_signals: list[str] = Field(default_factory=list)
    selected: bool = False
    rejection_reason: str | None = None
    job_id: str | None = None
    action: str | None = None
    status: str | None = None
    role_category: str | None = None
    remote_type: str | None = None


class AshbyBoardExpansionRead(BaseModel):
    parent_job_id: str
    company_id: str | None = None
    board_slug: str | None = None
    status: str
    reason: str
    postings_seen: int = 0
    postings_listed: int = 0
    postings_selected: int = 0
    jobs_created: int = 0
    jobs_existing: int = 0
    jobs_failed: int = 0
    parent_deactivated: bool = False
    created_job_ids: list[str] = Field(default_factory=list)
    existing_job_ids: list[str] = Field(default_factory=list)
    candidates: list[AshbyBoardExpansionCandidateRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    attempt_id: str | None = None
