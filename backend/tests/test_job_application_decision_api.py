import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db

from job_application_decision_helpers import create_job, create_user_profile


@pytest.fixture
async def job_decision_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def test_route_list_contains_status_counts(app):
    routes = {getattr(route, "path", "") for route in app.routes}

    assert "/api/v1/job-decisions/status-counts" in routes


@pytest.mark.asyncio
async def test_create_list_status_counts_get_update_archive_and_delete(job_decision_client, db_session):
    create_user_profile(db_session)
    job = create_job(db_session)

    created = await job_decision_client.post(
        f"/api/v1/job-decisions/jobs/{job.id}",
        json={"status": "interested", "notes": "Apply this week"},
    )
    assert created.status_code == 201
    data = created.json()
    assert data["job_id"] == job.id
    assert data["status"] == "interested"
    assert data["user_profile_id"]

    fetched = await job_decision_client.get(f"/api/v1/job-decisions/jobs/{job.id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == data["id"]

    listed = await job_decision_client.get("/api/v1/job-decisions")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["job_title"] == "AI Engineer"

    counts = await job_decision_client.get("/api/v1/job-decisions/status-counts")
    assert counts.status_code == 200
    assert counts.json()["interested"] == 1
    assert counts.json()["total"] == 1

    updated = await job_decision_client.patch(
        f"/api/v1/job-decisions/{data['id']}",
        json={"status": "applied"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "applied"

    archived = await job_decision_client.post(f"/api/v1/job-decisions/{data['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    deleted = await job_decision_client.delete(f"/api/v1/job-decisions/{data['id']}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_real_job_id_style_returns_created_and_unknown_job_returns_not_found(job_decision_client, db_session):
    create_user_profile(db_session)
    job = create_job(db_session)

    response = await job_decision_client.post(f"/api/v1/job-decisions/jobs/{job.id}", json={})
    assert response.status_code == 201

    missing = await job_decision_client.post("/api/v1/job-decisions/jobs/74c6dc4d-8323-4484-ba5d-missing", json={})
    assert missing.status_code == 404
    assert missing.json()["error"]["message"] == "Job not found"


@pytest.mark.asyncio
async def test_status_counts_is_not_treated_as_decision_id(job_decision_client, db_session):
    create_user_profile(db_session)

    response = await job_decision_client.get("/api/v1/job-decisions/status-counts")

    assert response.status_code == 200
    body = response.json()
    assert body["interested"] == 0
    assert body["applied"] == 0
    assert body["archived"] == 0
    assert body["needs_custom_resume"] == 0
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_api_rejects_arbitrary_user_profile_id(job_decision_client, db_session):
    create_user_profile(db_session)
    job = create_job(db_session)

    response = await job_decision_client.post(
        f"/api/v1/job-decisions/jobs/{job.id}",
        json={"user_profile_id": "other-profile"},
    )

    assert response.status_code == 422
