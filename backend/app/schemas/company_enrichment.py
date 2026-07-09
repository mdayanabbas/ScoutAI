from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.discovery import DiscoveryCandidateRead
from app.utils.enums import (
    CompanyEnrichmentDecision,
    CompanyEnrichmentResolver,
    CompanyEnrichmentStatus,
)


class CompanyEnrichmentAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    discovery_candidate_id: str
    status: CompanyEnrichmentStatus
    resolver: CompanyEnrichmentResolver
    proposed_website_url: str | None = None
    proposed_domain: str | None = None
    confidence: float | None = None
    decision: CompanyEnrichmentDecision | None = None
    reason: str | None = None
    error_message: str | None = None
    evidence: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_evidence_json(cls, value: Any) -> Any:
        if isinstance(value, dict):
            if "evidence" not in value and "evidence_json" in value:
                value["evidence"] = value["evidence_json"]
            return value
        if hasattr(value, "evidence_json"):
            return {
                "id": value.id,
                "discovery_candidate_id": value.discovery_candidate_id,
                "status": value.status,
                "resolver": value.resolver,
                "proposed_website_url": value.proposed_website_url,
                "proposed_domain": value.proposed_domain,
                "confidence": value.confidence,
                "decision": value.decision,
                "reason": value.reason,
                "error_message": value.error_message,
                "evidence": value.evidence_json,
                "started_at": value.started_at,
                "finished_at": value.finished_at,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        return value


class ManualCompanyDomainInput(BaseModel):
    website_url: str = Field(min_length=1)


class CandidateEnrichmentResult(BaseModel):
    candidate: DiscoveryCandidateRead
    attempts: list[CompanyEnrichmentAttemptRead]
    company_id: str | None = None
    decision: CompanyEnrichmentDecision
    resolved_domain: str | None = None
    message: str


class RunEnrichmentResult(BaseModel):
    discovery_run_id: str
    candidates_examined: int
    candidates_resolved: int
    companies_created: int
    companies_matched: int
    candidates_unresolved: int
    candidates_failed: int
    results: list[CandidateEnrichmentResult]
