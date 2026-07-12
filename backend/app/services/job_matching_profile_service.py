import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationAppError
from app.matching.profile_normalization import (
    MAX_COMPANY_SIZES,
    MAX_COMPANY_STAGES,
    MAX_COUNTRIES,
    MAX_EXCLUDED_COMPANIES,
    MAX_EXCLUDED_TITLES,
    MAX_LOCATIONS,
    MAX_NOTES_CHARS,
    MAX_ROLE_CATEGORIES,
    MAX_SENIORITY,
    MAX_SKILLS,
    MAX_TARGET_TITLES,
    MAX_TECHNOLOGIES,
    normalize_company_id,
    normalize_company_size,
    normalize_company_stage,
    normalize_country,
    normalize_currency,
    normalize_employment_type,
    normalize_location,
    normalize_profile_list,
    normalize_remote_type,
    normalize_role_category,
    normalize_seniority,
    normalize_skill_entries,
    normalize_skill_name,
    normalize_target_title,
    normalize_technology_name,
)
from app.models.job_matching_profile import JobMatchingProfile
from app.repositories.job_matching_profile_repository import JobMatchingProfileRepository
from app.repositories.profile_repository import UserProfileRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProfileCompleteness:
    completeness_score: int
    completed_sections: list[str]
    missing_sections: list[str]


class JobMatchingProfileService:
    def __init__(self, session: Session) -> None:
        self.user_profile_repository = UserProfileRepository(session)
        self.repository = JobMatchingProfileRepository(session)

    def get_for_current_profile(self) -> JobMatchingProfile:
        user_profile = self._require_user_profile()
        profile = self.repository.get_by_user_profile_id(user_profile.id)
        if profile is None:
            raise NotFoundError("Job matching profile not found")
        logger.info("Matching profile requested", extra={"user_profile_id": user_profile.id})
        return _attach_completeness(profile, self.calculate_completeness(profile))

    def create_or_replace(self, data: Any) -> JobMatchingProfile:
        user_profile = self._require_user_profile()
        normalized = self._normalize(_data_to_dict(data, exclude_unset=False), partial=False)
        profile = self.repository.create_or_update(user_profile.id, normalized)
        logger.info("Matching profile created or replaced", extra={"user_profile_id": user_profile.id})
        return _attach_completeness(profile, self.calculate_completeness(profile))

    def partial_update(self, data: Any) -> JobMatchingProfile:
        user_profile = self._require_user_profile()
        profile = self.repository.get_by_user_profile_id(user_profile.id)
        if profile is None:
            raise NotFoundError("Job matching profile not found")
        normalized = self._normalize(_data_to_dict(data, exclude_unset=True), partial=True)
        updated = self.repository.update_profile(profile, normalized)
        logger.info("Matching profile updated", extra={"user_profile_id": user_profile.id})
        return _attach_completeness(updated, self.calculate_completeness(updated))

    def reset(self) -> None:
        user_profile = self._require_user_profile()
        profile = self.repository.get_by_user_profile_id(user_profile.id)
        if profile is not None:
            self.repository.delete_profile(profile)
        logger.info("Matching profile reset", extra={"user_profile_id": user_profile.id})

    def calculate_completeness(self, profile: JobMatchingProfile) -> ProfileCompleteness:
        completed: list[str] = []
        missing: list[str] = []
        score = 0

        def add(section: str, points: int, present: bool) -> None:
            nonlocal score
            if present:
                completed.append(section)
                score += points
            else:
                missing.append(section)

        add("target_roles", 20, bool(profile.target_titles_json or profile.target_role_categories_json))
        add("skills_or_technologies", 20, bool(profile.skills_json or profile.technologies_json))
        add("experience_or_seniority", 15, profile.years_of_experience is not None or bool(profile.preferred_seniority_json))
        add("location_or_remote", 15, bool(profile.preferred_locations_json or profile.preferred_countries_json or profile.accepted_remote_types_json))
        add("employment_type", 10, bool(profile.accepted_employment_types_json))
        add("salary_preference", 5, profile.minimum_salary is not None)
        add("work_authorization", 5, profile.visa_sponsorship_required is not None or bool(profile.work_authorization_countries_json))
        add("company_preference", 5, bool(profile.preferred_company_stages_json or profile.preferred_company_sizes_json))
        add("exclusions", 5, bool(profile.excluded_titles_json or profile.excluded_role_categories_json or profile.excluded_company_ids_json or profile.excluded_locations_json))
        score = min(score, 100)
        logger.info("Profile completeness calculated", extra={"score": score})
        return ProfileCompleteness(score, completed, missing)

    def _require_user_profile(self):
        user_profile = self.user_profile_repository.get_first_profile()
        if user_profile is None:
            raise NotFoundError("User profile not found")
        return user_profile

    def _normalize(self, values: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        list_fields = {
            "target_titles": ("target_titles_json", normalize_target_title, MAX_TARGET_TITLES),
            "target_role_categories": ("target_role_categories_json", normalize_role_category, MAX_ROLE_CATEGORIES),
            "preferred_seniority": ("preferred_seniority_json", normalize_seniority, MAX_SENIORITY),
            "preferred_locations": ("preferred_locations_json", normalize_location, MAX_LOCATIONS),
            "preferred_countries": ("preferred_countries_json", normalize_country, MAX_COUNTRIES),
            "accepted_remote_types": ("accepted_remote_types_json", normalize_remote_type, MAX_SENIORITY),
            "accepted_employment_types": ("accepted_employment_types_json", normalize_employment_type, MAX_SENIORITY),
            "work_authorization_countries": ("work_authorization_countries_json", normalize_country, MAX_COUNTRIES),
            "preferred_company_stages": ("preferred_company_stages_json", normalize_company_stage, MAX_COMPANY_STAGES),
            "preferred_company_sizes": ("preferred_company_sizes_json", normalize_company_size, MAX_COMPANY_SIZES),
            "excluded_titles": ("excluded_titles_json", normalize_target_title, MAX_EXCLUDED_TITLES),
            "excluded_role_categories": ("excluded_role_categories_json", normalize_role_category, MAX_ROLE_CATEGORIES),
            "excluded_company_ids": ("excluded_company_ids_json", normalize_company_id, MAX_EXCLUDED_COMPANIES),
            "excluded_locations": ("excluded_locations_json", normalize_location, MAX_LOCATIONS),
        }
        for public_name, (column_name, normalizer, maximum) in list_fields.items():
            if public_name in values:
                normalized[column_name] = normalize_profile_list(values.get(public_name), normalizer, maximum=maximum, field_name=public_name)
            elif not partial:
                normalized[column_name] = []
        if "skills" in values:
            normalized["skills_json"] = normalize_skill_entries(values.get("skills"), maximum=MAX_SKILLS, field_name="skills", name_normalizer=normalize_skill_name)
        elif not partial:
            normalized["skills_json"] = []
        if "technologies" in values:
            normalized["technologies_json"] = normalize_skill_entries(values.get("technologies"), maximum=MAX_TECHNOLOGIES, field_name="technologies", name_normalizer=normalize_technology_name)
        elif not partial:
            normalized["technologies_json"] = []
        for scalar in ("matching_enabled", "visa_sponsorship_required", "willing_to_relocate"):
            if scalar in values:
                normalized[scalar] = values[scalar]
            elif not partial and scalar == "matching_enabled":
                normalized[scalar] = True
        for numeric in ("years_of_experience", "minimum_salary"):
            if numeric in values:
                value = values[numeric]
                if value is not None and value < 0:
                    raise ValidationAppError(f"{numeric} cannot be negative")
                normalized[numeric] = value
            elif not partial:
                normalized[numeric] = None
        if "salary_currency" in values:
            normalized["salary_currency"] = normalize_currency(values.get("salary_currency"))
        elif not partial:
            normalized["salary_currency"] = None
        if "notes" in values:
            notes = values.get("notes")
            if notes is not None and len(notes) > MAX_NOTES_CHARS:
                raise ValidationAppError("notes exceeds maximum", {"notes": f"maximum {MAX_NOTES_CHARS}"})
            normalized["notes"] = notes
        elif not partial:
            normalized["notes"] = None
        logger.info("Matching profile input normalized")
        return normalized


def _attach_completeness(profile: JobMatchingProfile, completeness: ProfileCompleteness) -> JobMatchingProfile:
    setattr(profile, "completeness_score", completeness.completeness_score)
    setattr(profile, "completed_sections", completeness.completed_sections)
    setattr(profile, "missing_sections", completeness.missing_sections)
    return profile


def _data_to_dict(data: Any, *, exclude_unset: bool) -> dict[str, Any]:
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=exclude_unset)
    return dict(data)

