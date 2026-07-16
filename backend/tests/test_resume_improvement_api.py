import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db

from job_application_decision_helpers import create_job, create_user_profile


@pytest.fixture
async def resume_improvement_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_job_resume_improvement_works(resume_improvement_client, db_session):
    create_user_profile(db_session)
    job = create_job(db_session)

    response = await resume_improvement_client.post(
        f"/api/v1/resume-improvements/jobs/{job.id}",
        json={"update_decision": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job.id
    assert body["improvement_summary"]
    assert "description" not in body
    assert "raw_text" not in response.text
    assert "storage_path" not in response.text


@pytest.mark.asyncio
async def test_post_decision_resume_improvement_works(resume_improvement_client, db_session):
    create_user_profile(db_session)
    job = create_job(db_session)
    decision = await resume_improvement_client.post(f"/api/v1/job-decisions/jobs/{job.id}", json={})
    assert decision.status_code == 201

    response = await resume_improvement_client.post(
        f"/api/v1/resume-improvements/decisions/{decision.json()['id']}",
        json={"include_remote_fit_suggestions": False},
    )

    assert response.status_code == 200
    assert response.json()["decision_id"] == decision.json()["id"]
    assert response.json()["remote_fit_suggestions"] == []


@pytest.mark.asyncio
async def test_resume_improvement_missing_resources_and_invalid_request(resume_improvement_client, db_session):
    create_user_profile(db_session)

    missing_job = await resume_improvement_client.post("/api/v1/resume-improvements/jobs/missing", json={})
    assert missing_job.status_code == 404

    missing_decision = await resume_improvement_client.post("/api/v1/resume-improvements/decisions/missing", json={})
    assert missing_decision.status_code == 404

    job = create_job(db_session)
    invalid = await resume_improvement_client.post(
        f"/api/v1/resume-improvements/jobs/{job.id}",
        json={"user_profile_id": "profile-1"},
    )
    assert invalid.status_code == 422
