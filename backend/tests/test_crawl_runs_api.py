import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def crawl_runs_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _create_company(client: AsyncClient, name: str = "Crawl Co") -> str:
    domain = name.lower().replace(" ", "-")
    response = await client.post(
        "/api/v1/companies",
        json={"name": name, "website_url": f"https://{domain}.example"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_crawl_run(client: AsyncClient, company_id: str) -> dict:
    response = await client.post(f"/api/v1/companies/{company_id}/crawl-runs")
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_create_crawl_run(crawl_runs_api_client: AsyncClient):
    company_id = await _create_company(crawl_runs_api_client)

    response = await crawl_runs_api_client.post(
        f"/api/v1/companies/{company_id}/crawl-runs"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["company_id"] == company_id
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_crawl_run_with_missing_company_returns_404(
    crawl_runs_api_client: AsyncClient,
):
    response = await crawl_runs_api_client.post(
        "/api/v1/companies/missing/crawl-runs"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_company_crawl_runs_returns_paginated_response(
    crawl_runs_api_client: AsyncClient,
):
    company_id = await _create_company(crawl_runs_api_client)
    await _create_crawl_run(crawl_runs_api_client, company_id)

    response = await crawl_runs_api_client.get(
        f"/api/v1/companies/{company_id}/crawl-runs"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["has_next"] is False
    assert data["has_prev"] is False
    assert data["items"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_recent_crawl_runs(crawl_runs_api_client: AsyncClient):
    company_id = await _create_company(crawl_runs_api_client)
    await _create_crawl_run(crawl_runs_api_client, company_id)

    response = await crawl_runs_api_client.get("/api/v1/crawl-runs")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["company_id"] == company_id


@pytest.mark.asyncio
async def test_list_recent_crawl_runs_supports_status_filter(
    crawl_runs_api_client: AsyncClient,
):
    company_id = await _create_company(crawl_runs_api_client)
    first = await _create_crawl_run(crawl_runs_api_client, company_id)
    await _create_crawl_run(crawl_runs_api_client, company_id)
    await crawl_runs_api_client.post(
        f"/api/v1/crawl-runs/{first['id']}/mark-running"
    )

    response = await crawl_runs_api_client.get("/api/v1/crawl-runs?status=running")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "running"


@pytest.mark.asyncio
async def test_get_crawl_run(crawl_runs_api_client: AsyncClient):
    company_id = await _create_company(crawl_runs_api_client)
    crawl_run = await _create_crawl_run(crawl_runs_api_client, company_id)

    response = await crawl_runs_api_client.get(
        f"/api/v1/crawl-runs/{crawl_run['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == crawl_run["id"]


@pytest.mark.asyncio
async def test_get_missing_crawl_run_returns_404(
    crawl_runs_api_client: AsyncClient,
):
    response = await crawl_runs_api_client.get("/api/v1/crawl-runs/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_mark_running_updates_status_and_started_at(
    crawl_runs_api_client: AsyncClient,
):
    company_id = await _create_company(crawl_runs_api_client)
    crawl_run = await _create_crawl_run(crawl_runs_api_client, company_id)

    response = await crawl_runs_api_client.post(
        f"/api/v1/crawl-runs/{crawl_run['id']}/mark-running"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["started_at"] is not None


@pytest.mark.asyncio
async def test_mark_success_updates_status_and_counts(
    crawl_runs_api_client: AsyncClient,
):
    company_id = await _create_company(crawl_runs_api_client)
    crawl_run = await _create_crawl_run(crawl_runs_api_client, company_id)

    response = await crawl_runs_api_client.post(
        f"/api/v1/crawl-runs/{crawl_run['id']}/mark-success",
        json={"pages_found": 10, "pages_crawled": 8},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["finished_at"] is not None
    assert response.json()["pages_found"] == 10
    assert response.json()["pages_crawled"] == 8


@pytest.mark.asyncio
async def test_mark_failed_updates_status_and_error(
    crawl_runs_api_client: AsyncClient,
):
    company_id = await _create_company(crawl_runs_api_client)
    crawl_run = await _create_crawl_run(crawl_runs_api_client, company_id)

    response = await crawl_runs_api_client.post(
        f"/api/v1/crawl-runs/{crawl_run['id']}/mark-failed",
        json={"error_message": "Timeout while fetching homepage"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["finished_at"] is not None
    assert response.json()["error_message"] == "Timeout while fetching homepage"


@pytest.mark.asyncio
async def test_negative_mark_success_counts_return_validation_error(
    crawl_runs_api_client: AsyncClient,
):
    company_id = await _create_company(crawl_runs_api_client)
    crawl_run = await _create_crawl_run(crawl_runs_api_client, company_id)

    response = await crawl_runs_api_client.post(
        f"/api/v1/crawl-runs/{crawl_run['id']}/mark-success",
        json={"pages_found": -1, "pages_crawled": 8},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_empty_mark_failed_error_message_returns_validation_error(
    crawl_runs_api_client: AsyncClient,
):
    company_id = await _create_company(crawl_runs_api_client)
    crawl_run = await _create_crawl_run(crawl_runs_api_client, company_id)

    response = await crawl_runs_api_client.post(
        f"/api/v1/crawl-runs/{crawl_run['id']}/mark-failed",
        json={"error_message": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
