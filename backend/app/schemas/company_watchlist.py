from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WatchStatus = Literal["watching", "interested", "contacted", "applied", "paused", "archived"]
WatchPriority = Literal["high", "medium", "low"]
RemoteInterest = Literal["remote_worldwide", "remote_india", "hybrid_possible", "unknown"]
JuniorFriendlinessSignal = Literal["strong", "moderate", "weak", "unknown"]


class CompanyWatchlistCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str | None = None
    company_name: str | None = Field(default=None, max_length=255)
    company_domain: str | None = Field(default=None, max_length=255)
    company_url: str | None = Field(default=None, max_length=1000)
    watch_status: WatchStatus = "watching"
    priority: WatchPriority = "medium"
    interest_reason: str | None = Field(default=None, max_length=5000)
    target_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    remote_interest: RemoteInterest = "unknown"
    junior_friendliness_signal: JuniorFriendlinessSignal = "unknown"

    @field_validator("company_id", "company_name", "company_domain", "company_url", "interest_reason", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("target_roles", "preferred_locations", "tags", mode="before")
    @classmethod
    def clean_string_list(cls, value):
        if value is None:
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @model_validator(mode="after")
    def require_company_reference(self):
        if not self.company_id and not self.company_name:
            raise ValueError("company_id or company_name is required")
        return self


class CompanyWatchlistUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, max_length=255)
    company_domain: str | None = Field(default=None, max_length=255)
    company_url: str | None = Field(default=None, max_length=1000)
    watch_status: WatchStatus | None = None
    priority: WatchPriority | None = None
    interest_reason: str | None = Field(default=None, max_length=5000)
    target_roles: list[str] | None = None
    preferred_locations: list[str] | None = None
    notes: str | None = Field(default=None, max_length=5000)
    tags: list[str] | None = None
    remote_interest: RemoteInterest | None = None
    junior_friendliness_signal: JuniorFriendlinessSignal | None = None
    last_reviewed_at: datetime | None = None

    @field_validator("company_name", "company_domain", "company_url", "interest_reason", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("target_roles", "preferred_locations", "tags", mode="before")
    @classmethod
    def clean_optional_string_list(cls, value):
        if value is None:
            return None
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class CompanyWatchlistFromJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, max_length=255)
    company_domain: str | None = Field(default=None, max_length=255)
    company_url: str | None = Field(default=None, max_length=1000)
    watch_status: WatchStatus = "watching"
    priority: WatchPriority = "medium"
    interest_reason: str | None = Field(default=None, max_length=5000)
    target_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    remote_interest: RemoteInterest = "unknown"
    junior_friendliness_signal: JuniorFriendlinessSignal = "unknown"

    @field_validator("company_name", "company_domain", "company_url", "interest_reason", "notes", mode="before")
    @classmethod
    def empty_string_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("target_roles", "preferred_locations", "tags", mode="before")
    @classmethod
    def clean_string_list(cls, value):
        if value is None:
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class CompanyWatchlistJobRead(BaseModel):
    id: str
    company_id: str
    company_name: str | None = None
    title: str
    normalized_title: str | None = None
    role_category: str | None = None
    location: str | None = None
    remote_type: str | None = None
    salary_min: int | float | str | None = None
    salary_max: int | float | str | None = None
    salary_currency: str | None = None
    job_url: str | None = None
    apply_url: str | None = None
    source_platform: str | None = None
    status: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    match_tier: str | None = None
    total_score: float | None = None
    eligibility_status: str | None = None


class CompanyWatchlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str | None = None
    company_name: str
    company_domain: str | None = None
    company_url: str | None = None
    watch_status: str
    priority: str
    interest_reason: str | None = None
    target_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    remote_interest: str
    junior_friendliness_signal: str
    last_reviewed_at: datetime | None = None
    last_job_seen_at: datetime | None = None
    job_count: int = 0
    recommended_job_count: int = 0
    latest_job_title: str | None = None
    latest_job_published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class CompanyWatchlistListResponse(BaseModel):
    items: list[CompanyWatchlistResponse]
    total: int
    limit: int
    offset: int


class CompanyWatchlistStatsResponse(BaseModel):
    total: int = 0
    watching: int = 0
    interested: int = 0
    contacted: int = 0
    applied: int = 0
    paused: int = 0
    archived: int = 0
    high_priority: int = 0
    medium_priority: int = 0
    low_priority: int = 0
    with_recommended_jobs: int = 0
    with_recent_jobs: int = 0
    needs_review: int = 0


class CompanyWatchlistJobsResponse(BaseModel):
    watchlist_item: CompanyWatchlistResponse
    jobs: list[CompanyWatchlistJobRead]
    total: int
    limit: int
    offset: int
