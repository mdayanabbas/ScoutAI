from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobMatchScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_ids: list[str] | None = None
    limit: int | None = Field(default=None, ge=1, le=500)
    force: bool = False


class JobMatchBatchItemRead(BaseModel):
    job_id: str | None = None
    status: str
    match_id: str | None = None
    eligibility_status: str | None = None
    reason: str | None = None


class JobMatchBatchRead(BaseModel):
    jobs_examined: int
    jobs_scored: int
    jobs_created: int
    jobs_updated: int
    jobs_failed: int
    eligible: int
    stretch: int
    uncertain: int
    unsuitable: int
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    results: list[JobMatchBatchItemRead]


class JobMatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    job_matching_profile_id: str
    eligibility_status: str
    eligibility_reason: str | None = None
    remote_eligibility: str
    match_tier: str
    total_score: float
    role_score: float
    seniority_score: float
    remote_score: float
    experience_score: float
    employment_type_score: float
    skills_score: float
    technology_score: float
    salary_score: float
    company_score: float
    confidence_score: float
    hard_filter_reasons: list[str] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    actionability_status: str | None = None
    valid_job_url: bool | None = None
    valid_apply_url: bool | None = None
    scoring_version: str
    scored_at: datetime
    created_at: datetime
    updated_at: datetime | None = None
    is_stale: bool = False

    @model_validator(mode="before")
    @classmethod
    def map_json_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return value
        return {
            "id": value.id,
            "job_id": value.job_id,
            "job_matching_profile_id": value.job_matching_profile_id,
            "eligibility_status": value.eligibility_status,
            "eligibility_reason": value.eligibility_reason,
            "remote_eligibility": value.remote_eligibility,
            "match_tier": value.match_tier,
            "total_score": value.total_score,
            "role_score": value.role_score,
            "seniority_score": value.seniority_score,
            "remote_score": value.remote_score,
            "experience_score": value.experience_score,
            "employment_type_score": value.employment_type_score,
            "skills_score": value.skills_score,
            "technology_score": value.technology_score,
            "salary_score": value.salary_score,
            "company_score": value.company_score,
            "confidence_score": value.confidence_score,
            "hard_filter_reasons": value.hard_filter_reasons_json or [],
            "positive_signals": value.positive_signals_json or [],
            "negative_signals": value.negative_signals_json or [],
            "missing_information": value.missing_information_json or [],
            "score_breakdown": value.score_breakdown_json or {},
            "actionability_status": (value.score_breakdown_json or {}).get("actionability_status"),
            "valid_job_url": (value.score_breakdown_json or {}).get("valid_job_url"),
            "valid_apply_url": (value.score_breakdown_json or {}).get("valid_apply_url"),
            "scoring_version": value.scoring_version,
            "scored_at": value.scored_at,
            "created_at": value.created_at,
            "updated_at": value.updated_at,
            "is_stale": getattr(value, "is_stale", False),
        }


class JobMatchListItemRead(BaseModel):
    job_id: str
    company_id: str
    company_name: str | None = None
    title: str
    role_category: str | None = None
    seniority: str | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    location: str | None = None
    remote_type: str | None = None
    remote_eligibility: str
    employment_type: str | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    job_url: str | None = None
    apply_url: str | None = None
    published_at: datetime | None = None
    enrichment_status: str
    eligibility_status: str
    eligibility_reason: str | None = None
    match_tier: str
    total_score: float
    role_score: float
    remote_score: float
    seniority_score: float
    experience_score: float
    actionability_status: str | None = None
    valid_job_url: bool | None = None
    valid_apply_url: bool | None = None
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    scored_at: datetime
    is_stale: bool = False

    @classmethod
    def from_match(cls, match: Any, *, is_stale: bool = False) -> "JobMatchListItemRead":
        job = match.job
        company = getattr(job, "company", None)
        breakdown = match.score_breakdown_json or {}
        return cls(
            job_id=job.id,
            company_id=job.company_id,
            company_name=getattr(company, "name", None),
            title=job.title,
            role_category=str(getattr(job.role_category, "value", job.role_category)) if job.role_category else None,
            seniority=job.seniority,
            experience_min=job.experience_min,
            experience_max=job.experience_max,
            location=job.location,
            remote_type=str(getattr(job.remote_type, "value", job.remote_type)) if job.remote_type else None,
            remote_eligibility=match.remote_eligibility,
            employment_type=job.employment_type,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            job_url=job.job_url,
            apply_url=job.apply_url,
            published_at=job.published_at,
            enrichment_status=job.enrichment_status,
            eligibility_status=match.eligibility_status,
            eligibility_reason=match.eligibility_reason,
            match_tier=match.match_tier,
            total_score=match.total_score,
            role_score=match.role_score,
            remote_score=match.remote_score,
            seniority_score=match.seniority_score,
            experience_score=match.experience_score,
            actionability_status=breakdown.get("actionability_status"),
            valid_job_url=breakdown.get("valid_job_url"),
            valid_apply_url=breakdown.get("valid_apply_url"),
            positive_signals=match.positive_signals_json or [],
            negative_signals=match.negative_signals_json or [],
            missing_information=match.missing_information_json or [],
            scored_at=match.scored_at,
            is_stale=is_stale,
        )


class JobMatchListRead(BaseModel):
    items: list[JobMatchListItemRead]
    total: int
    limit: int
    offset: int
