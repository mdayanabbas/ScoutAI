from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

REMOTE_DISCOVERY_SOURCES = {
    "himalayas",
    "we_work_remotely",
    "remotive",
    "hacker_news",
    "ycombinator",
    "ashby",
}


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


class HackerNewsRemoteDiscoveryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    feeds: list[str] = Field(default_factory=lambda: ["jobs"])
    limit: int = Field(default=100, ge=1, le=500)
    lookback_days: int = Field(default=30, ge=1, le=365)
    minimum_score: int | None = Field(default=0, ge=0)
    include_items_without_website: bool = True
    enrich_domains: bool = True
    ingest_jobs: bool = True
    enrich_jobs: bool = True
    score_jobs: bool = True


class YCombinatorRemoteDiscoveryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_pages: int = Field(default=5, ge=1, le=25)
    remote_only: bool = False
    include_recent_only: bool = True
    lookback_days: int = Field(default=60, ge=1, le=365)
    ingest_jobs: bool = True
    enrich_jobs: bool = True
    score_jobs: bool = True


class AshbyRemoteDiscoveryOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    board_slugs: list[str] = Field(default_factory=list)
    max_jobs_per_board: int = Field(default=50, ge=1, le=200)
    enrich_jobs: bool = True
    score_jobs: bool = True


class RemoteJobDiscoveryRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False
    sources: list[str] | None = None
    score_after_ingestion: bool | None = True
    himalayas: HimalayasRemoteDiscoveryOptions | None = None
    we_work_remotely: WWRRemoteDiscoveryOptions | None = None
    remotive: RemotiveRemoteDiscoveryOptions | None = None
    hacker_news: HackerNewsRemoteDiscoveryOptions | None = None
    ycombinator: YCombinatorRemoteDiscoveryOptions | None = None
    ashby: AshbyRemoteDiscoveryOptions | None = None

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
    candidates_found: int = 0
    candidates_normalized: int = 0
    candidates_deferred: int = 0
    candidates_failed: int = 0
    companies_created: int = 0
    companies_matched: int = 0
    domains_resolved: int = 0
    domains_unresolved: int = 0
    jobs_skipped: int = 0
    jobs_enriched: int = 0
    provider_records_seen: int = 0
    unique_records: int = 0
    accepted_jobs_count: int = 0
    rejected_samples_count: int = 0
    accepted_jobs: list[dict[str, Any]] = Field(default_factory=list)
    rejected_samples: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class RemoteJobDiscoveryPlanRead(BaseModel):
    profile_id: str
    enabled_sources: list[str]
    disabled_sources: list[str]
    cooldowns: dict[str, dict[str, Any]]
    himalayas: dict[str, Any] | None = None
    we_work_remotely: dict[str, Any] | None = None
    remotive: dict[str, Any] | None = None
    hacker_news: dict[str, Any] | None = None
    ycombinator: dict[str, Any] | None = None
    ashby: dict[str, Any] | None = None
    available_sources: list[dict[str, Any]] = Field(default_factory=list)
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
    recommendation_scope: str = "global"
    recommendation_source_filter: list[str] = Field(default_factory=list)
    recommendation_job_ids_count: int = 0
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    warnings: list[str] = Field(default_factory=list)
