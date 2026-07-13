from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HimalayasDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False
    max_queries: int | None = Field(default=None, ge=1, le=50)
    max_pages_per_query: int | None = Field(default=None, ge=1, le=10)
    score_after_ingestion: bool | None = None


class HimalayasQueryPlanRead(BaseModel):
    current_profile_target_titles: list[str] = Field(default_factory=list)
    normalized_queries: list[str]
    worldwide_passes: list[dict[str, Any]]
    india_passes: list[dict[str, Any]]
    query_count: int
    generated_from_profile: bool
    warnings: list[str] = Field(default_factory=list)


class HimalayasQueryResult(BaseModel):
    query: str
    query_type: str
    country: str | None = None
    worldwide: bool | None = None
    pages_requested: int = 0
    jobs_received: int = 0
    jobs_unique: int = 0
    jobs_accepted: int = 0
    jobs_rejected: int = 0
    error: str | None = None


class HimalayasRejectedCandidateSummary(BaseModel):
    source_item_id: str
    title: str
    company_name: str
    rejection_reason: str
    remote_eligibility: str | None = None
    seniority: str | None = None


class HimalayasAcceptedJobSummary(BaseModel):
    job_id: str
    company_name: str
    title: str
    remote_eligibility: str
    seniority: str | None = None
    employment_type: str | None = None
    salary_text: str | None = None
    job_url: str | None = None
    action: str
    eligibility_status: str | None = None
    match_tier: str | None = None
    total_score: float | None = None


class HimalayasDiscoveryResult(BaseModel):
    discovery_run_id: str | None = None
    status: str
    reason: str | None = None
    profile_id: str | None = None
    previous_run_id: str | None = None
    next_eligible_at: datetime | None = None
    queries_planned: int = 0
    queries_completed: int = 0
    queries_failed: int = 0
    provider_requests_attempted: int = 0
    provider_pages_completed: int = 0
    provider_records_seen: int = 0
    malformed_provider_records: int = 0
    unique_records: int = 0
    candidates_created: int = 0
    candidates_existing: int = 0
    candidates_rejected: int = 0
    companies_created: int = 0
    companies_existing: int = 0
    jobs_created: int = 0
    jobs_existing: int = 0
    jobs_updated: int = 0
    jobs_scored: int = 0
    jobs_failed: int = 0
    accepted_jobs: list[HimalayasAcceptedJobSummary] = Field(default_factory=list)
    rejected_samples: list[HimalayasRejectedCandidateSummary] = Field(default_factory=list)
    query_results: list[HimalayasQueryResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime
    duration_ms: int
