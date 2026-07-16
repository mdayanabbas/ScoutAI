import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db

from job_application_decision_helpers import create_job, create_user_profile


@pytest.fixture
async def application_packet_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_job_generates_packet(application_packet_client, db_session):
    create_user_profile(db_session)
    job = create_job(db_session)

    response = await application_packet_client.post(
        f"/api/v1/application-packets/jobs/{job.id}",
        json={},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job.id
    assert body["decision_id"]
    assert body["application_positioning"]
    assert body["resume_focus"] is not None
    assert body["suggested_apply_plan"]
    assert "description" not in body
    assert "raw_payload" not in response.text


@pytest.mark.asyncio
async def test_post_decision_generates_packet(application_packet_client, db_session):
    create_user_profile(db_session)
    job = create_job(db_session)
    decision = await application_packet_client.post(f"/api/v1/job-decisions/jobs/{job.id}", json={})
    assert decision.status_code == 201

    response = await application_packet_client.post(
        f"/api/v1/application-packets/decisions/{decision.json()['id']}",
        json={"include_cold_dm_outline": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision_id"] == decision.json()["id"]
    assert body["cold_dm_outline"] is None


@pytest.mark.asyncio
async def test_missing_job_and_decision_return_404(application_packet_client, db_session):
    create_user_profile(db_session)

    missing_job = await application_packet_client.post("/api/v1/application-packets/jobs/missing", json={})
    assert missing_job.status_code == 404

    missing_decision = await application_packet_client.post("/api/v1/application-packets/decisions/missing", json={})
    assert missing_decision.status_code == 404


@pytest.mark.asyncio
async def test_request_rejects_user_profile_id(application_packet_client, db_session):
    create_user_profile(db_session)
    job = create_job(db_session)

    response = await application_packet_client.post(
        f"/api/v1/application-packets/jobs/{job.id}",
        json={"user_profile_id": "profile-1"},
    )

    assert response.status_code == 422
