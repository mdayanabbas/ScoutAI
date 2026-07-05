from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
)


class UserProfileObj:
    id = "profile-1"
    display_name = "Scout"
    target_roles = ["AI Engineer"]
    preferred_locations = []
    remote_preference = "unknown"
    years_experience = 3
    skills = ["Python"]
    strong_skills = []
    weak_skills = []
    preferred_company_stages = []
    preferred_company_sizes = []
    created_at = datetime.now(timezone.utc)
    updated_at = None


def test_user_profile_create_accepts_list_fields():
    profile = UserProfileCreate(target_roles=["AI Engineer"], skills=["Python"])
    assert profile.skills == ["Python"]


def test_user_profile_update_allows_partial_update():
    assert UserProfileUpdate(display_name="Scout").display_name == "Scout"


def test_user_profile_read_supports_from_attributes():
    assert UserProfileRead.model_validate(UserProfileObj()).id == "profile-1"


def test_negative_years_experience_fails():
    with pytest.raises(ValidationError):
        UserProfileCreate(years_experience=-1)
