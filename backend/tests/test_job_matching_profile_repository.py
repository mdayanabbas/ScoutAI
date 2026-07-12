from app.models.user_profile import UserProfile
from app.repositories.job_matching_profile_repository import JobMatchingProfileRepository


def _user(db_session):
    user = UserProfile(display_name="Scout")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_repository_create_get_update_idempotent_and_delete(db_session):
    user = _user(db_session)
    repo = JobMatchingProfileRepository(db_session)

    profile = repo.create_or_update(user.id, {"target_titles_json": ["Backend Engineer"]})
    fetched = repo.get_by_id(profile.id)
    by_user = repo.get_by_user_profile_id(user.id)
    updated = repo.create_or_update(user.id, {"target_titles_json": ["AI Engineer"]})

    assert fetched.id == profile.id
    assert by_user.id == profile.id
    assert updated.id == profile.id
    assert updated.target_titles_json == ["AI Engineer"]
    assert repo.exists_for_user_profile(user.id)

    repo.delete_profile(updated)
    assert repo.get_by_user_profile_id(user.id) is None
    assert db_session.get(UserProfile, user.id) is not None

