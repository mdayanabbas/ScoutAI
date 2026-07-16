from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_profile_id: str
    filename: str
    original_filename: str
    content_type: str | None = None
    file_size_bytes: int
    is_active: bool
    parse_status: str
    parse_error: str | None = None
    parsed_summary: dict | None = None
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    certifications: list[dict] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None
    parsed_at: datetime | None = None


class ResumeListResponse(BaseModel):
    items: list[ResumeResponse]
    total: int
    limit: int
    offset: int


class ResumeUploadResponse(BaseModel):
    resume: ResumeResponse
    warnings: list[str] = Field(default_factory=list)


class ResumeActivateResponse(BaseModel):
    resume_id: str
    is_active: bool
    previous_active_resume_id: str | None = None
