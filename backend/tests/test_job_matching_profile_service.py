import pytest

from app.core.errors import NotFoundError, ValidationAppError
from app.models.user_profile import UserProfile
from app.services.job_matching_profile_service import JobMatchingProfileService


def _user(db_session):
    user = UserProfile(display_name="Scout")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_service_put_patch_reset_and_normalization(db_session):
    _user(db_session)
    service = JobMatchingProfileService(db_session)

    profile = service.create_or_replace(
        {
            "target_titles": [" backend engineer ", "Backend Engineer"],
            "skills": [
                {"name": "Python", "proficiency": "intermediate", "years_experience": 2},
                {"name": "python", "proficiency": "expert", "years_experience": 3},
            ],
            "accepted_remote_types": ["remote"],
            "minimum_salary": 60000,
            "salary_currency": "usd",
        }
    )

    assert profile.target_titles_json == ["Backend Engineer"]
    assert profile.skills_json == [{"name": "Python", "proficiency": "expert", "years_experience": 3.0}]
    assert profile.accepted_remote_types_json == ["remote_worldwide"]
    assert profile.salary_currency == "USD"
    assert profile.completeness_score > 0

    patched = service.partial_update({"target_titles": [], "notes": "hello"})
    assert patched.target_titles_json == []
    assert patched.skills_json == profile.skills_json
    assert patched.notes == "hello"

    cleared = service.partial_update({"minimum_salary": None})
    assert cleared.minimum_salary is None

    service.reset()
    with pytest.raises(NotFoundError):
        service.get_for_current_profile()


def test_service_validation_and_completeness(db_session):
    _user(db_session)
    service = JobMatchingProfileService(db_session)

    empty = service.create_or_replace({})
    assert empty.completeness_score == 0
    assert "target_roles" in empty.missing_sections

    complete = service.create_or_replace(
        {
            "target_titles": ["AI Engineer"],
            "skills": [{"name": "Python"}],
            "years_of_experience": 5,
            "accepted_remote_types": ["remote"],
            "accepted_employment_types": ["full_time"],
            "minimum_salary": 100000,
            "visa_sponsorship_required": False,
            "preferred_company_stages": ["seed"],
            "excluded_company_ids": ["11111111-1111-1111-1111-111111111111"],
        }
    )
    assert complete.completeness_score == 100

    with pytest.raises(ValidationAppError):
        service.partial_update({"target_role_categories": ["not_real"]})
    with pytest.raises(ValidationAppError):
        service.partial_update({"preferred_seniority": ["wizard"]})
    with pytest.raises(ValidationAppError):
        service.partial_update({"minimum_salary": -1})
    with pytest.raises(ValidationAppError):
        service.partial_update({"excluded_company_ids": ["not-a-uuid"]})


def test_service_requires_user_profile(db_session):
    with pytest.raises(NotFoundError):
        JobMatchingProfileService(db_session).create_or_replace({})

