from app.models.user_profile import UserProfile
from app.repositories.profile_repository import UserProfileRepository
from app.utils.enums import RemoteType


def test_profile_repository_create_get_first_update(db_session):
    repo = UserProfileRepository(db_session)
    profile = repo.create_profile(
        UserProfile(
            display_name="Scout User",
            target_roles=["AI Engineer"],
            remote_preference=RemoteType.REMOTE_WORLDWIDE,
            skills=["Python", "SQL"],
        )
    )

    assert repo.get_by_id(profile.id) == profile
    assert repo.get_first_profile() == profile
    assert repo.count() == 1

    repo.update_profile(profile, {"years_experience": 5})
    assert repo.get_first_profile().years_experience == 5
