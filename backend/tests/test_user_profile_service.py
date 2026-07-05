import pytest

from app.core.errors import NotFoundError
from app.services.user_profile_service import UserProfileService


def test_profile_create_or_update_creates_then_updates(db_session):
    service = UserProfileService(db_session)

    profile = service.create_or_update_profile({"display_name": "Scout"})
    updated = service.create_or_update_profile({"display_name": "Scout AI"})

    assert updated.id == profile.id
    assert updated.display_name == "Scout AI"


def test_update_profile_requires_existing_profile(db_session):
    service = UserProfileService(db_session)

    with pytest.raises(NotFoundError):
        service.update_profile({"display_name": "Scout"})
