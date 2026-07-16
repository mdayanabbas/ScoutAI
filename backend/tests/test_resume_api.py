import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db

from job_application_decision_helpers import create_user_profile


@pytest.fixture
async def resume_client(app, db_session, tmp_path, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "RESUME_UPLOADS_DIR", str(tmp_path / "uploads"))

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_resume_api_upload_list_active_reparse_delete(resume_client, db_session):
    create_user_profile(db_session)
    upload = await resume_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.txt", b"Skills\nPython, FastAPI", "text/plain")},
        data={"make_active": "true"},
    )
    assert upload.status_code == 200
    body = upload.json()
    resume_id = body["resume"]["id"]
    assert body["resume"]["is_active"] is True
    assert "storage_path" not in body["resume"]
    assert "raw_text" not in body["resume"]

    assert (await resume_client.get("/api/v1/resumes")).json()["total"] == 1
    assert (await resume_client.get("/api/v1/resumes/active")).json()["id"] == resume_id
    assert (await resume_client.get(f"/api/v1/resumes/{resume_id}")).status_code == 200
    assert (await resume_client.post(f"/api/v1/resumes/{resume_id}/activate")).status_code == 200
    assert (await resume_client.post(f"/api/v1/resumes/{resume_id}/reparse")).status_code == 200
    assert (await resume_client.delete(f"/api/v1/resumes/{resume_id}")).status_code == 204


@pytest.mark.asyncio
async def test_resume_api_missing_resume_returns_404(resume_client, db_session):
    create_user_profile(db_session)
    response = await resume_client.get("/api/v1/resumes/missing")
    assert response.status_code == 404
