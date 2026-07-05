from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.enums import JobStatus, RemoteType, RoleCategory


class JobBase(BaseModel):
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
    normalized_title: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
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
