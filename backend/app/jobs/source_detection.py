from dataclasses import dataclass, field
from typing import Any

from app.utils.enums import JobSourceType


@dataclass(frozen=True)
class JobSourceDetectionResult:
    source_type: JobSourceType
    original_url: str | None
    normalized_url: str | None = None
    canonical_url: str | None = None
    normalized_domain: str | None = None
    provider: str | None = None
    company_slug: str | None = None
    job_identifier: str | None = None
    board_slug: str | None = None
    path: str | None = None
    is_first_party: bool = False
    supported: bool = False
    confidence: float = 0.0
    reason: str = "unsupported_job_source"
    evidence: dict[str, Any] = field(default_factory=dict)
