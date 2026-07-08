from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoveryRunStatus,
    DiscoverySource,
)


class DiscoveryEvidenceInput(BaseModel):
    evidence_type: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    title: str | None = None
    excerpt: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class RawStartupCandidate(BaseModel):
    source_identifier: str = Field(min_length=1)
    name: str = Field(min_length=1)
    website_url: str | None = None
    description: str | None = None
    country: str | None = None
    evidence: list[DiscoveryEvidenceInput] = Field(default_factory=list)
    raw_payload: dict[str, Any] | None = None


class NormalizedStartupCandidate(BaseModel):
    source_identifier: str
    name: str
    website_url: str | None = None
    normalized_domain: str | None = None
    description: str | None = None
    country: str | None = None
    evidence: list[DiscoveryEvidenceInput] = Field(default_factory=list)


class ManualDiscoveryRequest(BaseModel):
    candidates: list[RawStartupCandidate] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class DiscoveryEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    evidence_type: str
    source_url: str
    title: str | None = None
    excerpt: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_metadata_json(cls, value: Any) -> Any:
        if isinstance(value, dict):
            if "metadata" not in value and "metadata_json" in value:
                value["metadata"] = value["metadata_json"]
            return value
        if hasattr(value, "metadata_json"):
            return {
                "id": value.id,
                "evidence_type": value.evidence_type,
                "source_url": value.source_url,
                "title": value.title,
                "excerpt": value.excerpt,
                "published_at": value.published_at,
                "metadata": value.metadata_json,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        return value


class DiscoveryRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: DiscoverySource
    status: DiscoveryRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    candidates_found: int
    candidates_normalized: int
    companies_created: int
    companies_matched: int
    candidates_rejected: int
    candidates_failed: int
    error_message: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_metadata_json(cls, value: Any) -> Any:
        if isinstance(value, dict):
            if "metadata" not in value and "metadata_json" in value:
                value["metadata"] = value["metadata_json"]
            return value
        if hasattr(value, "metadata_json"):
            return {
                "id": value.id,
                "source": value.source,
                "status": value.status,
                "started_at": value.started_at,
                "finished_at": value.finished_at,
                "candidates_found": value.candidates_found,
                "candidates_normalized": value.candidates_normalized,
                "companies_created": value.companies_created,
                "companies_matched": value.companies_matched,
                "candidates_rejected": value.candidates_rejected,
                "candidates_failed": value.candidates_failed,
                "error_message": value.error_message,
                "metadata": value.metadata_json,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
            }
        return value


class DiscoveryCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    discovery_run_id: str
    source: DiscoverySource
    source_identifier: str
    raw_name: str
    raw_website_url: str | None = None
    raw_description: str | None = None
    raw_country: str | None = None
    normalized_name: str | None = None
    normalized_website_url: str | None = None
    normalized_domain: str | None = None
    normalized_description: str | None = None
    normalized_country: str | None = None
    status: DiscoveryCandidateStatus
    decision: DiscoveryDecision | None = None
    rejection_reason: str | None = None
    error_message: str | None = None
    matched_company_id: str | None = None
    raw_payload: dict[str, Any] | None = None
    evidence: list[DiscoveryEvidenceRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None


class DiscoveryRunResult(BaseModel):
    run: DiscoveryRunRead
    candidates: list[DiscoveryCandidateRead]
