from sqlalchemy.exc import IntegrityError

from app.models.job_matching_profile import JobMatchingProfile
from app.models.user_profile import UserProfile


def test_job_matching_profile_model_defaults_and_one_to_one(db_session):
    user = UserProfile(display_name="Scout")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = JobMatchingProfile(user_profile_id=user.id)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.matching_enabled is True
    assert profile.target_titles_json == []
    assert profile.skills_json == []
    assert profile.minimum_salary is None
    assert profile.created_at is not None

    duplicate = JobMatchingProfile(user_profile_id=user.id)
    db_session.add(duplicate)
    try:
        db_session.commit()
    except IntegrityError:
        db_session.rollback()
    else:
        raise AssertionError("expected unique user_profile_id constraint")


def test_json_defaults_are_independent(db_session):
    first_user = UserProfile(display_name="First")
    second_user = UserProfile(display_name="Second")
    db_session.add_all([first_user, second_user])
    db_session.commit()

    first = JobMatchingProfile(user_profile_id=first_user.id)
    second = JobMatchingProfile(user_profile_id=second_user.id)
    db_session.add_all([first, second])
    db_session.commit()

    first.target_titles_json.append("Backend Engineer")

    assert second.target_titles_json == []

