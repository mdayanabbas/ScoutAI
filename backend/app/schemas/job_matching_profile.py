from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.matching.profile_normalization import (
    MAX_COUNTRIES,
    MAX_EXCLUDED_COMPANIES,
    MAX_EXCLUDED_TITLES,
    MAX_LOCATIONS,
    MAX_NOTES_CHARS,
    MAX_SKILLS,
    MAX_TARGET_TITLES,
    MAX_TECHNOLOGIES,
)


class MatchingSkillInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    proficiency: str | None = None
    years_experience: float | None = Field(default=None, ge=0)


class MatchingTechnologyInput(MatchingSkillInput):
    pass


class JobMatchingProfileBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matching_enabled: bool = True
    target_titles: list[str] = Field(default_factory=list, max_length=MAX_TARGET_TITLES)
    target_role_categories: list[str] = Field(default_factory=list)
    preferred_seniority: list[str] = Field(default_factory=list)
    years_of_experience: float | None = Field(default=None, ge=0)
    skills: list[MatchingSkillInput] = Field(default_factory=list, max_length=MAX_SKILLS)
    technologies: list[MatchingTechnologyInput] = Field(default_factory=list, max_length=MAX_TECHNOLOGIES)
    preferred_locations: list[str] = Field(default_factory=list, max_length=MAX_LOCATIONS)
    preferred_countries: list[str] = Field(default_factory=list, max_length=MAX_COUNTRIES)
    accepted_remote_types: list[str] = Field(default_factory=list)
    accepted_employment_types: list[str] = Field(default_factory=list)
    minimum_salary: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, max_length=8)
    visa_sponsorship_required: bool | None = None
    work_authorization_countries: list[str] = Field(default_factory=list)
    willing_to_relocate: bool | None = None
    preferred_company_stages: list[str] = Field(default_factory=list)
    preferred_company_sizes: list[str] = Field(default_factory=list)
    excluded_titles: list[str] = Field(default_factory=list, max_length=MAX_EXCLUDED_TITLES)
    excluded_role_categories: list[str] = Field(default_factory=list)
    excluded_company_ids: list[str] = Field(default_factory=list, max_length=MAX_EXCLUDED_COMPANIES)
    excluded_locations: list[str] = Field(default_factory=list, max_length=MAX_LOCATIONS)
    notes: str | None = Field(default=None, max_length=MAX_NOTES_CHARS)


class JobMatchingProfileCreate(JobMatchingProfileBase):
    pass


class JobMatchingProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matching_enabled: bool | None = None
    target_titles: list[str] | None = None
    target_role_categories: list[str] | None = None
    preferred_seniority: list[str] | None = None
    years_of_experience: float | None = Field(default=None, ge=0)
    skills: list[MatchingSkillInput] | None = None
    technologies: list[MatchingTechnologyInput] | None = None
    preferred_locations: list[str] | None = None
    preferred_countries: list[str] | None = None
    accepted_remote_types: list[str] | None = None
    accepted_employment_types: list[str] | None = None
    minimum_salary: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, max_length=8)
    visa_sponsorship_required: bool | None = None
    work_authorization_countries: list[str] | None = None
    willing_to_relocate: bool | None = None
    preferred_company_stages: list[str] | None = None
    preferred_company_sizes: list[str] | None = None
    excluded_titles: list[str] | None = None
    excluded_role_categories: list[str] | None = None
    excluded_company_ids: list[str] | None = None
    excluded_locations: list[str] | None = None
    notes: str | None = Field(default=None, max_length=MAX_NOTES_CHARS)


class JobMatchingProfileRead(JobMatchingProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_profile_id: str
    completeness_score: int
    completed_sections: list[str]
    missing_sections: list[str]
    created_at: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_json_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return value
        mapping = {
            "target_titles": "target_titles_json",
            "target_role_categories": "target_role_categories_json",
            "preferred_seniority": "preferred_seniority_json",
            "skills": "skills_json",
            "technologies": "technologies_json",
            "preferred_locations": "preferred_locations_json",
            "preferred_countries": "preferred_countries_json",
            "accepted_remote_types": "accepted_remote_types_json",
            "accepted_employment_types": "accepted_employment_types_json",
            "work_authorization_countries": "work_authorization_countries_json",
            "preferred_company_stages": "preferred_company_stages_json",
            "preferred_company_sizes": "preferred_company_sizes_json",
            "excluded_titles": "excluded_titles_json",
            "excluded_role_categories": "excluded_role_categories_json",
            "excluded_company_ids": "excluded_company_ids_json",
            "excluded_locations": "excluded_locations_json",
        }
        data = {
            "id": value.id,
            "user_profile_id": value.user_profile_id,
            "matching_enabled": value.matching_enabled,
            "years_of_experience": value.years_of_experience,
            "minimum_salary": value.minimum_salary,
            "salary_currency": value.salary_currency,
            "visa_sponsorship_required": value.visa_sponsorship_required,
            "willing_to_relocate": value.willing_to_relocate,
            "notes": value.notes,
            "created_at": value.created_at,
            "updated_at": value.updated_at,
            "completeness_score": getattr(value, "completeness_score", 0),
            "completed_sections": getattr(value, "completed_sections", []),
            "missing_sections": getattr(value, "missing_sections", []),
        }
        for public_name, attr_name in mapping.items():
            data[public_name] = getattr(value, attr_name) or []
        return data


class JobMatchingProfileSummaryRead(BaseModel):
    id: str
    user_profile_id: str
    matching_enabled: bool
    completeness_score: int
    completed_sections: list[str]
    missing_sections: list[str]
