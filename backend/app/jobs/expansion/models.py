from dataclasses import dataclass, field


@dataclass(frozen=True)
class AshbyBoardExpansionCandidate:
    posting_id: str | None
    title: str | None
    canonical_job_url: str | None
    apply_url: str | None = None
    department: str | None = None
    team: str | None = None
    location: str | None = None
    employment_type: str | None = None
    match_score: float = 0.0
    matched_signals: list[str] = field(default_factory=list)
    rejected_signals: list[str] = field(default_factory=list)
    selected: bool = False
    rejection_reason: str | None = None
    job_id: str | None = None
    action: str | None = None
    status: str | None = None
    role_category: str | None = None
    remote_type: str | None = None


@dataclass(frozen=True)
class AshbyBoardExpansionResult:
    parent_job_id: str
    company_id: str | None
    board_slug: str | None
    status: str
    reason: str
    postings_seen: int = 0
    postings_listed: int = 0
    postings_selected: int = 0
    jobs_created: int = 0
    jobs_existing: int = 0
    jobs_failed: int = 0
    parent_deactivated: bool = False
    created_job_ids: list[str] = field(default_factory=list)
    existing_job_ids: list[str] = field(default_factory=list)
    candidates: list[AshbyBoardExpansionCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    attempt_id: str | None = None

