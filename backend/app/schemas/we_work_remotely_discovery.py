from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WWRDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False
    include_all_other: bool | None = None
    max_items_per_feed: int | None = Field(default=None, ge=1, le=500)
    score_after_ingestion: bool | None = None


class WWRFeedPlanRead(BaseModel):
    enabled_feeds: list[dict[str, Any]]
    profile_target_roles: list[str] = Field(default_factory=list)
    accepted_employment_types: list[str] = Field(default_factory=list)
    remote_eligibility_policy: list[str] = Field(default_factory=list)
    maximum_items: int
    cooldown_active: bool = False
    previous_run_id: str | None = None
    next_eligible_at: datetime | None = None
    warnings: list[str] = Field(default_factory=list)


class WWRFeedResult(BaseModel):
    feed_type: str
    status: str
    http_status: int | None = None
    not_modified: bool = False
    items_received: int = 0
    unique_items: int = 0
    valid_items: int = 0
    malformed_items: int = 0
    accepted_items: int = 0
    rejected_items: int = 0
    error: str | None = None


class WWRRejectedCandidateSummary(BaseModel):
    source_item_id: str
    title: str | None = None
    company_name: str | None = None
    rejection_reason: str
    remote_eligibility: str | None = None
    seniority: str | None = None


class WWRAcceptedJobSummary(BaseModel):
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


class WWRDiscoveryResult(BaseModel):
    discovery_run_id: str | None = None
    status: str
    reason: str | None = None
    profile_id: str | None = None
    previous_run_id: str | None = None
    next_eligible_at: datetime | None = None
    feeds_planned: int = 0
    feeds_completed: int = 0
    feeds_failed: int = 0
    feeds_not_modified: int = 0
    feed_items_seen: int = 0
    unique_items: int = 0
    malformed_items: int = 0
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
    accepted_jobs: list[WWRAcceptedJobSummary] = Field(default_factory=list)
    rejected_samples: list[WWRRejectedCandidateSummary] = Field(default_factory=list)
    feed_results: list[WWRFeedResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime
    duration_ms: int
