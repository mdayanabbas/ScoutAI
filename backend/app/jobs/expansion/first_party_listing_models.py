from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FirstPartyListingCandidate:
    title: str | None
    original_url: str | None = None
    canonical_url: str | None = None
    source_strategy: str = "unknown"
    posting_identifier: str | None = None
    department: str | None = None
    team: str | None = None
    location: str | None = None
    employment_type: str | None = None
    description_excerpt: str | None = None
    confidence: float = 0.0
    scope_score: float = 0.0
    matched_signals: list[str] = field(default_factory=list)
    rejected_signals: list[str] = field(default_factory=list)
    selected: bool = False
    rejection_reason: str | None = None
    structured_data: dict[str, Any] | None = None
    job_id: str | None = None
    action: str | None = None
    status: str | None = None
    role_category: str | None = None
    remote_type: str | None = None


@dataclass(frozen=True)
class FirstPartyListingChild:
    job_id: str
    title: str
    job_url: str | None
    role_category: str | None = None
    location: str | None = None
    remote_type: str | None = None
    action: str = "created"
    status: str = "succeeded"


@dataclass(frozen=True)
class FirstPartyListingExtractionResult:
    source_url: str
    canonical_url: str
    candidates: list[FirstPartyListingCandidate] = field(default_factory=list)
    candidate_count: int = 0
    parser_strategy: str = "none"
    listing_detected: bool = False
    confidence: float = 0.0
    reason: str = "first_party_listing_no_roles"
    warnings: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FirstPartyListingExpansionResult:
    parent_job_id: str
    company_id: str | None = None
    status: str = "unresolved"
    reason: str = "first_party_listing_no_roles"
    links_seen: int = 0
    candidates_selected: int = 0
    detail_pages_fetched: int = 0
    jobs_created: int = 0
    jobs_existing: int = 0
    jobs_failed: int = 0
    parent_deactivated: bool = False
    created_job_ids: list[str] = field(default_factory=list)
    existing_job_ids: list[str] = field(default_factory=list)
    failed_candidates: list[dict[str, str | None]] = field(default_factory=list)
    children: list[FirstPartyListingChild] = field(default_factory=list)
    candidates: list[FirstPartyListingCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    attempt_id: str | None = None
