import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db

from company_watchlist_helpers import create_company, create_company_job, create_job_match


@pytest.fixture
async def company_watchlist_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def test_route_list_contains_company_watchlist_stats(app):
    routes = {getattr(route, "path", "") for route in app.routes}

    assert "/api/v1/company-watchlist/stats" in routes


@pytest.mark.asyncio
async def test_api_create_list_stats_get_update_archive_delete(company_watchlist_client, db_session):
    company = create_company(db_session)

    created = await company_watchlist_client.post(
        "/api/v1/company-watchlist",
        json={"company_id": company.id, "priority": "high", "tags": ["target"]},
    )
    assert created.status_code == 201
    data = created.json()
    assert data["company_id"] == company.id
    assert data["company_name"] == company.name
    assert data["priority"] == "high"

    listed = await company_watchlist_client.get("/api/v1/company-watchlist")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    stats = await company_watchlist_client.get("/api/v1/company-watchlist/stats")
    assert stats.status_code == 200
    assert stats.json()["total"] == 1
    assert stats.json()["high_priority"] == 1

    fetched = await company_watchlist_client.get(f"/api/v1/company-watchlist/{data['id']}")
    assert fetched.status_code == 200

    updated = await company_watchlist_client.patch(
        f"/api/v1/company-watchlist/{data['id']}",
        json={"watch_status": "interested", "notes": "Founder-led"},
    )
    assert updated.status_code == 200
    assert updated.json()["watch_status"] == "interested"

    archived = await company_watchlist_client.post(f"/api/v1/company-watchlist/{data['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["watch_status"] == "archived"

    deleted = await company_watchlist_client.delete(f"/api/v1/company-watchlist/{data['id']}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_api_jobs_from_job_missing_and_duplicate(company_watchlist_client, db_session):
    company = create_company(db_session)
    job = create_company_job(db_session, company)
    create_job_match(db_session, job)

    from_job = await company_watchlist_client.post(f"/api/v1/company-watchlist/from-job/{job.id}", json={})
    assert from_job.status_code == 201
    item = from_job.json()
    assert item["company_id"] == company.id

    duplicate = await company_watchlist_client.post("/api/v1/company-watchlist", json={"company_id": company.id})
    assert duplicate.status_code == 409

    jobs = await company_watchlist_client.get(f"/api/v1/company-watchlist/{item['id']}/jobs?recommended_only=true")
    assert jobs.status_code == 200
    body = jobs.json()
    assert body["total"] == 1
    assert "description" not in body["jobs"][0]
    assert body["jobs"][0]["match_tier"] == "strong_match"

    missing_company = await company_watchlist_client.post("/api/v1/company-watchlist", json={"company_id": "missing"})
    assert missing_company.status_code == 404

    missing_job = await company_watchlist_client.post("/api/v1/company-watchlist/from-job/missing", json={})
    assert missing_job.status_code == 404

    missing_item = await company_watchlist_client.get("/api/v1/company-watchlist/missing")
    assert missing_item.status_code == 404


@pytest.mark.asyncio
async def test_api_invalid_payload_returns_422(company_watchlist_client):
    response = await company_watchlist_client.post(
        "/api/v1/company-watchlist",
        json={"watch_status": "bad", "user_profile_id": "nope"},
    )

    assert response.status_code == 422

