from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AshbyPublicJobPosting:
    id: str | None = None
    title: str | None = None
    location: str | None = None
    secondary_locations: list[str] = field(default_factory=list)
    department: str | None = None
    team: str | None = None
    is_listed: bool | None = None
    is_remote: bool | None = None
    workplace_type: str | None = None
    employment_type: str | None = None
    description_html: str | None = None
    description_plain: str | None = None
    published_at: str | None = None
    job_url: str | None = None
    apply_url: str | None = None
    compensation: Any = None
    raw_index: int = 0


@dataclass(frozen=True)
class AshbyPublicJobBoardResponse:
    board_slug: str
    jobs: list[AshbyPublicJobPosting] = field(default_factory=list)
    status_code: int | None = None
    fetched_at: datetime | None = None
    response_size: int | None = None
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)

