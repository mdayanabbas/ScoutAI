from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class JobFieldValue:
    value: Any
    confidence: float
    source: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JobDetailExtractionResult:
    success: bool
    provider: str
    source_url: str
    canonical_url: str
    title: JobFieldValue | None = None
    description: JobFieldValue | None = None
    role_category: JobFieldValue | None = None
    seniority: JobFieldValue | None = None
    location: JobFieldValue | None = None
    remote_type: JobFieldValue | None = None
    employment_type: JobFieldValue | None = None
    experience_min: JobFieldValue | None = None
    experience_max: JobFieldValue | None = None
    salary_min: JobFieldValue | None = None
    salary_max: JobFieldValue | None = None
    salary_currency: JobFieldValue | None = None
    salary_text: JobFieldValue | None = None
    equity_mentioned: JobFieldValue | None = None
    apply_url: JobFieldValue | None = None
    visa_sponsorship: JobFieldValue | None = None
    work_authorization: JobFieldValue | None = None
    required_skills: JobFieldValue | None = None
    preferred_skills: JobFieldValue | None = None
    technologies: JobFieldValue | None = None
    published_at: JobFieldValue | None = None
    raw_role: JobFieldValue | None = None
    field_confidence: dict[str, float] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)

    def extracted_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for field_name in (
            "title",
            "description",
            "role_category",
            "seniority",
            "location",
            "remote_type",
            "employment_type",
            "experience_min",
            "experience_max",
            "salary_min",
            "salary_max",
            "salary_currency",
            "salary_text",
            "equity_mentioned",
            "apply_url",
            "visa_sponsorship",
            "work_authorization",
            "required_skills",
            "preferred_skills",
            "technologies",
            "published_at",
            "raw_role",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            item = value.value
            if isinstance(item, datetime):
                item = item.isoformat()
            data[field_name] = item
        return data
