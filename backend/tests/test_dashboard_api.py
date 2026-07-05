import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def dashboard_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _create_company(client: AsyncClient, name: str = "Dashboard Co") -> str:
    domain = name.lower().replace(" ", "-")
    response = await client.post(
        "/api/v1/companies",
        json={"name": name, "website_url": f"https://{domain}.example"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _seed_dashboard_data(client: AsyncClient) -> tuple[str, str]:
    company_id = await _create_company(client)
    job_response = await client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json={
            "title": "Remote AI Engineer",
            "job_url": "https://dashboard.example/jobs/ai",
            "status": "active",
            "remote_type": "remote_worldwide",
        },
    )
    assert job_response.status_code == 201
    crawl_response = await client.post(
        f"/api/v1/companies/{company_id}/crawl-runs"
    )
    await client.post(
        f"/api/v1/crawl-runs/{crawl_response.json()['id']}/mark-success",
        json={"pages_found": 2, "pages_crawled": 2},
    )
    agent_response = await client.post(
        "/api/v1/agent-runs",
        json={"company_id": company_id, "agent_name": "company_research"},
    )
    await client.post(
        f"/api/v1/agent-runs/{agent_response.json()['id']}/mark-failed",
        json={"error_message": "failed"},
    )
    return company_id, job_response.json()["id"]


@pytest.mark.asyncio
async def test_dashboard_summary_returns_expected_fields(
    dashboard_api_client: AsyncClient,
):
    await _seed_dashboard_data(dashboard_api_client)

    response = await dashboard_api_client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    data = response.json()
    expected_fields = {
        "total_companies",
        "total_jobs",
        "active_jobs",
        "remote_jobs",
        "companies_added_today",
        "jobs_added_today",
        "recent_crawl_runs",
        "successful_crawl_runs",
        "failed_crawl_runs",
        "recent_agent_runs",
        "successful_agent_runs",
        "failed_agent_runs",
    }
    assert expected_fields.issubset(data.keys())
    assert data["total_companies"] == 1
    assert data["total_jobs"] == 1
    assert data["active_jobs"] == 1
    assert data["remote_jobs"] == 1
    assert data["successful_crawl_runs"] == 1
    assert data["failed_agent_runs"] == 1


@pytest.mark.asyncio
async def test_dashboard_activity_returns_list_and_limit(
    dashboard_api_client: AsyncClient,
):
    await _seed_dashboard_data(dashboard_api_client)

    response = await dashboard_api_client.get("/api/v1/dashboard/activity?limit=2")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert {"type", "title", "description", "entity_id", "created_at"}.issubset(
        data[0].keys()
    )


@pytest.mark.asyncio
async def test_dashboard_activity_limit_above_100_returns_validation_error(
    dashboard_api_client: AsyncClient,
):
    response = await dashboard_api_client.get("/api/v1/dashboard/activity?limit=101")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_dashboard_overview_returns_summary_and_activity(
    dashboard_api_client: AsyncClient,
):
    await _seed_dashboard_data(dashboard_api_client)

    response = await dashboard_api_client.get("/api/v1/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "recent_activity" in data
    assert data["summary"]["total_companies"] == 1
    assert isinstance(data["recent_activity"], list)
