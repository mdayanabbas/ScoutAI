from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import RemoteType


class UserProfileBase(BaseModel):
    display_name: str | None = None
    target_roles: list[str] | None = None
    preferred_locations: list[str] | None = None
    remote_preference: RemoteType | None = RemoteType.UNKNOWN
    years_experience: int | None = Field(default=None, ge=0)
    skills: list[str] | None = None
    strong_skills: list[str] | None = None
    weak_skills: list[str] | None = None
    preferred_company_stages: list[str] | None = None
    preferred_company_sizes: list[str] | None = None


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    target_roles: list[str] | None = None
    preferred_locations: list[str] | None = None
    remote_preference: RemoteType | None = None
    years_experience: int | None = Field(default=None, ge=0)
    skills: list[str] | None = None
    strong_skills: list[str] | None = None
    weak_skills: list[str] | None = None
    preferred_company_stages: list[str] | None = None
    preferred_company_sizes: list[str] | None = None


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime | None = None
