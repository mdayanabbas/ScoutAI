from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

REMOTE_DISCOVERY_SOURCES = {"himalayas", "we_work_remotely", "remotive"}


class HimalayasRemoteDiscoveryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_queries: int | None = Field(default=None, ge=1, le=50)
    max_pages_per_query: int | None = Field(default=None, ge=1, le=10)


class WWRRemoteDiscoveryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_all_other: bool | None = None
    max_items_per_feed: int | None = Field(default=None, ge=1, le=500)


class RemotiveRemoteDiscoveryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_requests: int | None = Field(default=None, ge=1, le=10)
    limit_per_request: int | None = Field(default=None, ge=1, le=500)


class RemoteJobDiscoveryRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False
    sources: list[str] | None = None
    score_after_ingestion: bool | None = True
    himalayas: HimalayasRemoteDiscoveryOptions | None = None
    we_work_remotely: WWRRemoteDiscoveryOptions | None = None
    remotive: RemotiveRemoteDiscoveryOptions | None = None

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        normalized: list[str] = []
        for source in value:
            source_key = source.strip().lower()
            if source_key not in REMOTE_DISCOVERY_SOURCES:
                raise ValueError(f"Unsupported remote discovery source: {source}")
            if source_key not in normalized:
                normalized.append(source_key)
        return normalized


class RemoteRecommendationSummary(BaseModel):
    job_id: str
    company_name: str | None = None
    title: str
    remote_eligibility: str
    match_tier: str
    eligibility_status: str
    total_score: float
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    job_url: str | None = None
    apply_url: str | None = None
    eligibility_reason: str | None = None


class RemoteDiscoverySourceResult(BaseModel):
    source: str
    status: str
    reason: str | None = None
    discovery_run_id: str | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    jobs_created: int = 0
    jobs_existing: int = 0
    jobs_updated: int = 0
    jobs_scored: int = 0
    jobs_failed: int = 0
    candidates_created: int = 0
    candidates_existing: int = 0
    candidates_rejected: int = 0
    provider_records_seen: int = 0
    unique_records: int = 0
    accepted_jobs_count: int = 0
    rejected_samples_count: int = 0
    accepted_jobs: list[dict[str, Any]] = Field(default_factory=list)
    rejected_samples: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class RemoteJobDiscoveryPlanRead(BaseModel):
    profile_id: str
    enabled_sources: list[str]
    disabled_sources: list[str]
    cooldowns: dict[str, dict[str, Any]]
    himalayas: dict[str, Any] | None = None
    we_work_remotely: dict[str, Any] | None = None
    remotive: dict[str, Any] | None = None
    recommended_defaults: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class RemoteJobDiscoveryOrchestratorResult(BaseModel):
    status: Literal["succeeded", "partial", "failed", "skipped"]
    reason: str | None = None
    profile_id: str | None = None
    sources_planned: list[str] = Field(default_factory=list)
    sources_completed: int = 0
    sources_failed: int = 0
    sources_skipped: int = 0
    total_provider_records_seen: int = 0
    total_unique_records: int = 0
    total_candidates_created: int = 0
    total_candidates_existing: int = 0
    total_candidates_rejected: int = 0
    total_jobs_created: int = 0
    total_jobs_existing: int = 0
    total_jobs_updated: int = 0
    total_jobs_scored: int = 0
    total_jobs_failed: int = 0
    source_results: list[RemoteDiscoverySourceResult] = Field(default_factory=list)
    top_recommendations: list[RemoteRecommendationSummary] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    warnings: list[str] = Field(default_factory=list)
