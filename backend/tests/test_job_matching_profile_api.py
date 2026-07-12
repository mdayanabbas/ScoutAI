import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.models.user_profile import UserProfile
from app.repositories.profile_repository import UserProfileRepository


@pytest.fixture
async def matching_profile_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _create_user(db_session):
    return UserProfileRepository(db_session).create_profile(UserProfile(display_name="Scout"))


@pytest.mark.asyncio
async def test_matching_profile_api_lifecycle(matching_profile_api_client, db_session):
    _create_user(db_session)

    missing = await matching_profile_api_client.get("/api/v1/profile/job-matching")
    assert missing.status_code == 404

    created = await matching_profile_api_client.put(
        "/api/v1/profile/job-matching",
        json={
            "target_titles": [" backend engineer ", "Backend Engineer"],
            "skills": [{"name": "Python", "proficiency": "advanced"}],
            "minimum_salary": 60000,
            "salary_currency": "usd",
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["target_titles"] == ["Backend Engineer"]
    assert data["salary_currency"] == "USD"
    assert data["completeness_score"] > 0
    assert "target_titles_json" not in data

    patched = await matching_profile_api_client.patch(
        "/api/v1/profile/job-matching",
        json={"target_titles": [], "years_of_experience": 4},
    )
    assert patched.status_code == 200
    assert patched.json()["target_titles"] == []
    assert patched.json()["skills"] == [{"name": "Python", "proficiency": "advanced", "years_experience": None}]

    forbidden = await matching_profile_api_client.patch(
        "/api/v1/profile/job-matching",
        json={"user_profile_id": "other"},
    )
    assert forbidden.status_code == 422

    deleted = await matching_profile_api_client.delete("/api/v1/profile/job-matching")
    assert deleted.status_code == 200
    assert db_session.get(UserProfile, data["user_profile_id"]) is not None


@pytest.mark.asyncio
async def test_matching_profile_api_requires_user_and_validates(matching_profile_api_client):
    missing_user = await matching_profile_api_client.put("/api/v1/profile/job-matching", json={})
    assert missing_user.status_code == 404

    # Create the base profile through the existing endpoint, then verify validation behavior.
    await matching_profile_api_client.put("/api/v1/profile", json={"display_name": "Scout"})
    invalid = await matching_profile_api_client.put(
        "/api/v1/profile/job-matching",
        json={"years_of_experience": -1},
    )
    assert invalid.status_code == 422
