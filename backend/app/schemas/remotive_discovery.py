from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RemotiveDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False
    max_requests: int | None = Field(default=None, ge=1, le=10)
    limit_per_request: int | None = Field(default=None, ge=1, le=500)
    score_after_ingestion: bool | None = None


class RemotivePlannedRequestRead(BaseModel):
    request_type: str
    category: str | None = None
    search_term: str | None = None
    limit: int | None = None


class RemotiveQueryPlanRead(BaseModel):
    profile_target_roles: list[str] = Field(default_factory=list)
    planned_requests: list[RemotivePlannedRequestRead] = Field(default_factory=list)
    total_planned_requests: int
    configured_request_cap: int
    generated_from_profile: bool
    canonical_target_roles: list[str] = Field(default_factory=list)
    cooldown_active: bool = False
    previous_run_id: str | None = None
    next_eligible_at: datetime | None = None
    warnings: list[str] = Field(default_factory=list)


class RemotiveQueryResult(BaseModel):
    request_type: str
    category: str | None = None
    search_term: str | None = None
    http_status: int | None = None
    jobs_received: int = 0
    unique_jobs: int = 0
    jobs_accepted: int = 0
    jobs_rejected: int = 0
    malformed_records: int = 0
    error: str | None = None


class RemotiveAcceptedJobSummary(BaseModel):
    job_id: str
    company_name: str
    title: str
    remote_eligibility: str
    seniority: str | None = None
    employment_type: str | None = None
    salary_text: str | None = None
    published_at: datetime | None = None
    job_url: str | None = None
    action: str
    eligibility_status: str | None = None
    match_tier: str | None = None
    total_score: float | None = None
    attribution_label: str


class RemotiveRejectedCandidateSummary(BaseModel):
    source_item_id: str
    company_name: str | None = None
    title: str | None = None
    rejection_reason: str
    remote_eligibility: str | None = None
    seniority: str | None = None


class RemotiveDiscoveryResult(BaseModel):
    discovery_run_id: str | None = None
    status: str
    reason: str | None = None
    profile_id: str | None = None
    previous_run_id: str | None = None
    next_eligible_at: datetime | None = None
    requests_planned: int = 0
    requests_completed: int = 0
    requests_failed: int = 0
    provider_records_seen: int = 0
    unique_records: int = 0
    duplicate_records: int = 0
    malformed_records: int = 0
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
    accepted_jobs: list[RemotiveAcceptedJobSummary] = Field(default_factory=list)
    rejected_samples: list[RemotiveRejectedCandidateSummary] = Field(default_factory=list)
    query_results: list[RemotiveQueryResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime
    duration_ms: int
