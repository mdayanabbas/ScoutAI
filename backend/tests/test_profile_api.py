from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.schemas.user_profile import UserProfileRead


@pytest.fixture
async def profile_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _profile_payload() -> dict:
    return {
        "display_name": "Scout User",
        "target_roles": ["AI Engineer", "Backend Engineer"],
        "preferred_locations": ["Remote", "Bengaluru"],
        "remote_preference": "remote_worldwide",
        "years_experience": 5,
        "skills": ["Python", "SQL"],
        "strong_skills": ["Python"],
        "weak_skills": ["Frontend"],
        "preferred_company_stages": ["seed", "series_a"],
        "preferred_company_sizes": ["1-10", "11-50"],
    }


@pytest.mark.asyncio
async def test_get_profile_returns_404_when_missing(
    profile_api_client: AsyncClient,
):
    response = await profile_api_client.get("/api/v1/profile")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_put_profile_creates_profile(profile_api_client: AsyncClient):
    response = await profile_api_client.put(
        "/api/v1/profile",
        json=_profile_payload(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"]
    assert data["display_name"] == "Scout User"
    assert data["target_roles"] == ["AI Engineer", "Backend Engineer"]
    assert data["preferred_locations"] == ["Remote", "Bengaluru"]
    assert data["remote_preference"] == "remote_worldwide"
    assert data["years_experience"] == 5
    assert data["skills"] == ["Python", "SQL"]
    assert data["strong_skills"] == ["Python"]
    assert data["weak_skills"] == ["Frontend"]
    assert data["preferred_company_stages"] == ["seed", "series_a"]
    assert data["preferred_company_sizes"] == ["1-10", "11-50"]


@pytest.mark.asyncio
async def test_get_profile_returns_created_profile(profile_api_client: AsyncClient):
    create_response = await profile_api_client.put(
        "/api/v1/profile",
        json=_profile_payload(),
    )

    response = await profile_api_client.get("/api/v1/profile")

    assert response.status_code == 200
    assert response.json()["id"] == create_response.json()["id"]
    assert response.json()["display_name"] == "Scout User"


@pytest.mark.asyncio
async def test_put_profile_updates_existing_profile(profile_api_client: AsyncClient):
    create_response = await profile_api_client.put(
        "/api/v1/profile",
        json=_profile_payload(),
    )

    response = await profile_api_client.put(
        "/api/v1/profile",
        json={
            **_profile_payload(),
            "display_name": "Updated Scout",
            "years_experience": 6,
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == create_response.json()["id"]
    assert response.json()["display_name"] == "Updated Scout"
    assert response.json()["years_experience"] == 6


@pytest.mark.asyncio
async def test_patch_profile_partially_updates_profile(
    profile_api_client: AsyncClient,
):
    await profile_api_client.put("/api/v1/profile", json=_profile_payload())

    response = await profile_api_client.patch(
        "/api/v1/profile",
        json={"display_name": "Patched Scout"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Patched Scout"
    assert data["skills"] == ["Python", "SQL"]
    assert data["target_roles"] == ["AI Engineer", "Backend Engineer"]


@pytest.mark.asyncio
async def test_patch_profile_returns_404_when_missing(
    profile_api_client: AsyncClient,
):
    response = await profile_api_client.patch(
        "/api/v1/profile",
        json={"display_name": "Scout"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_invalid_years_experience_returns_validation_error(
    profile_api_client: AsyncClient,
):
    response = await profile_api_client.put(
        "/api/v1/profile",
        json={**_profile_payload(), "years_experience": -1},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_user_profile_response_schema_supports_from_attributes():
    class ProfileObj:
        id = "profile-1"
        display_name = "Scout"
        target_roles = ["AI Engineer"]
        preferred_locations = ["Remote"]
        remote_preference = "remote_worldwide"
        years_experience = 5
        skills = ["Python"]
        strong_skills = ["Python"]
        weak_skills = ["Frontend"]
        preferred_company_stages = ["seed"]
        preferred_company_sizes = ["1-10"]
        created_at = datetime.now(timezone.utc)
        updated_at = None

    assert UserProfileRead.model_validate(ProfileObj()).id == "profile-1"
