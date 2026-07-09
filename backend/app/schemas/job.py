from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.enums import JobStatus, RemoteType, RoleCategory


class JobBase(BaseModel):
    discovery_candidate_id: str | None = None
    title: str
    role_category: RoleCategory | None = RoleCategory.OTHER
    description: str | None = None
    location: str | None = None
    remote_type: RemoteType | None = RemoteType.UNKNOWN
    experience_min: int | None = Field(default=None, ge=0)
    experience_max: int | None = Field(default=None, ge=0)
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    job_url: str
    source_platform: str | None = None
    status: JobStatus = JobStatus.ACTIVE
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if (
            self.experience_min is not None
            and self.experience_max is not None
            and self.experience_min > self.experience_max
        ):
            raise ValueError("experience_min must be <= experience_max")
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must be <= salary_max")
        return self


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    discovery_candidate_id: str | None = None
    title: str | None = None
    role_category: RoleCategory | None = None
    description: str | None = None
    location: str | None = None
    remote_type: RemoteType | None = None
    experience_min: int | None = Field(default=None, ge=0)
    experience_max: int | None = Field(default=None, ge=0)
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    job_url: str | None = None
    source_platform: str | None = None
    status: JobStatus | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if (
            self.experience_min is not None
            and self.experience_max is not None
            and self.experience_min > self.experience_max
        ):
            raise ValueError("experience_min must be <= experience_max")
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must be <= salary_max")
        return self


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    company_name: str | None = None
    company_website_url: str | None = None
    normalized_title: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_company_fields(cls, value: Any) -> Any:
        return _map_company_fields(value)


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    company_name: str | None = None
    company_website_url: str | None = None
    discovery_candidate_id: str | None = None
    title: str
    normalized_title: str | None = None
    role_category: RoleCategory | None = None
    location: str | None = None
    remote_type: RemoteType | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    job_url: str | None = None
    source_platform: str | None = None
    status: JobStatus
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_company_fields(cls, value: Any) -> Any:
        return _map_company_fields(value)


def _map_company_fields(value: Any) -> Any:
    if isinstance(value, dict):
        if "company" in value and value["company"] is not None:
            company = value["company"]
            if isinstance(company, dict):
                value.setdefault("company_name", company.get("name"))
                value.setdefault("company_website_url", company.get("website_url"))
        return value
    try:
        company = getattr(value, "company", None)
    except Exception:
        company = None
    if company is not None:
        return {
            "id": value.id,
            "company_id": value.company_id,
            "company_name": getattr(company, "name", None),
            "company_website_url": getattr(company, "website_url", None),
            "discovery_candidate_id": getattr(value, "discovery_candidate_id", None),
            "title": value.title,
            "normalized_title": value.normalized_title,
            "role_category": value.role_category,
            "description": getattr(value, "description", None),
            "location": value.location,
            "remote_type": value.remote_type,
            "experience_min": value.experience_min,
            "experience_max": value.experience_max,
            "salary_min": value.salary_min,
            "salary_max": value.salary_max,
            "salary_currency": value.salary_currency,
            "job_url": value.job_url,
            "source_platform": value.source_platform,
            "status": value.status,
            "first_seen_at": value.first_seen_at,
            "last_seen_at": value.last_seen_at,
            "created_at": value.created_at,
            "updated_at": value.updated_at,
        }
    return value
