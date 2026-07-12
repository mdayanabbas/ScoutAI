from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.job_matching_profile import JobMatchingProfileCreate, JobMatchingProfileRead


def test_create_schema_rejects_internal_user_profile_id():
    with pytest.raises(ValidationError):
        JobMatchingProfileCreate(user_profile_id="other", target_titles=["Backend Engineer"])


def test_read_schema_maps_json_fields_without_internal_names():
    class Obj:
        id = "profile-1"
        user_profile_id = "user-1"
        matching_enabled = True
        target_titles_json = ["Backend Engineer"]
        target_role_categories_json = []
        preferred_seniority_json = []
        years_of_experience = 5
        skills_json = [{"name": "Python"}]
        technologies_json = []
        preferred_locations_json = []
        preferred_countries_json = []
        accepted_remote_types_json = []
        accepted_employment_types_json = []
        minimum_salary = None
        salary_currency = None
        visa_sponsorship_required = None
        work_authorization_countries_json = []
        willing_to_relocate = None
        preferred_company_stages_json = []
        preferred_company_sizes_json = []
        excluded_titles_json = []
        excluded_role_categories_json = []
        excluded_company_ids_json = []
        excluded_locations_json = []
        notes = None
        completeness_score = 40
        completed_sections = ["target_roles"]
        missing_sections = ["salary_preference"]
        created_at = datetime.now(timezone.utc)
        updated_at = None

    data = JobMatchingProfileRead.model_validate(Obj()).model_dump()

    assert data["target_titles"] == ["Backend Engineer"]
    assert data["skills"] == [{"name": "Python", "proficiency": None, "years_experience": None}]
    assert "target_titles_json" not in data

