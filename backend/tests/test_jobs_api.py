import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def jobs_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _create_company(client: AsyncClient, name: str = "Jobs Co") -> str:
    domain = name.lower().replace(" ", "-")
    response = await client.post(
        "/api/v1/companies",
        json={"name": name, "website_url": f"https://{domain}.example"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _job_payload(**overrides) -> dict:
    payload = {
        "title": "Senior AI Engineer",
        "role_category": "ai_engineer",
        "description": "Build applied AI systems.",
        "location": "Remote",
        "remote_type": "remote_worldwide",
        "job_url": "https://jobs.example/senior-ai-engineer",
        "source_platform": "company_website",
        "status": "active",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_create_company_job(jobs_api_client: AsyncClient):
    company_id = await _create_company(jobs_api_client)

    response = await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["company_id"] == company_id
    assert data["company_name"] == "Jobs Co"
    assert data["company_website_url"] == "jobs-co.example"
    assert data["title"] == "Senior AI Engineer"
    assert data["normalized_title"] == "senior ai engineer"
    assert data["role_category"] == "ai_engineer"
    assert data["location"] == "Remote"
    assert data["remote_type"] == "remote_worldwide"
    assert data["job_url"] == "https://jobs.example/senior-ai-engineer"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_same_job_updates_existing_job(jobs_api_client: AsyncClient):
    company_id = await _create_company(jobs_api_client)
    first = await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(),
    )

    second = await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(title="Principal AI Engineer"),
    )

    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["title"] == "Principal AI Engineer"
    assert second.json()["normalized_title"] == "principal ai engineer"

    list_response = await jobs_api_client.get("/api/v1/jobs")
    assert list_response.json()["total"] == 1


@pytest.mark.asyncio
async def test_create_job_with_missing_company_returns_404(
    jobs_api_client: AsyncClient,
):
    response = await jobs_api_client.post(
        "/api/v1/companies/missing/jobs",
        json=_job_payload(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_jobs_returns_paginated_response(jobs_api_client: AsyncClient):
    company_id = await _create_company(jobs_api_client)
    await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(),
    )

    response = await jobs_api_client.get("/api/v1/jobs")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["has_next"] is False
    assert data["has_prev"] is False
    assert data["items"][0]["title"] == "Senior AI Engineer"
    assert data["items"][0]["company_id"] == company_id
    assert data["items"][0]["company_name"] == "Jobs Co"
    assert data["items"][0]["company_website_url"] == "jobs-co.example"
    assert "description" not in data["items"][0]


@pytest.mark.asyncio
async def test_list_jobs_supports_search_and_filters(jobs_api_client: AsyncClient):
    company_id = await _create_company(jobs_api_client)
    await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(),
    )
    await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(
            title="Backend Engineer",
            role_category="backend_engineer",
            remote_type="hybrid",
            job_url="https://jobs.example/backend-engineer",
            status="inactive",
        ),
    )

    search_response = await jobs_api_client.get("/api/v1/jobs?search=senior")
    role_response = await jobs_api_client.get(
        "/api/v1/jobs?role_category=backend_engineer"
    )
    remote_response = await jobs_api_client.get("/api/v1/jobs?remote_type=hybrid")
    status_response = await jobs_api_client.get("/api/v1/jobs?status=inactive")

    assert search_response.json()["total"] == 1
    assert search_response.json()["items"][0]["title"] == "Senior AI Engineer"
    assert role_response.json()["total"] == 1
    assert role_response.json()["items"][0]["role_category"] == "backend_engineer"
    assert remote_response.json()["total"] == 1
    assert remote_response.json()["items"][0]["remote_type"] == "hybrid"
    assert status_response.json()["total"] == 1
    assert status_response.json()["items"][0]["status"] == "inactive"


@pytest.mark.asyncio
async def test_list_company_jobs_returns_only_that_company(
    jobs_api_client: AsyncClient,
):
    first_company_id = await _create_company(jobs_api_client, "First Co")
    second_company_id = await _create_company(jobs_api_client, "Second Co")
    await jobs_api_client.post(
        f"/api/v1/companies/{first_company_id}/jobs",
        json=_job_payload(job_url="https://jobs.example/first"),
    )
    await jobs_api_client.post(
        f"/api/v1/companies/{second_company_id}/jobs",
        json=_job_payload(job_url="https://jobs.example/second"),
    )

    response = await jobs_api_client.get(
        f"/api/v1/companies/{first_company_id}/jobs"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["company_id"] == first_company_id


@pytest.mark.asyncio
async def test_get_job_returns_full_job(jobs_api_client: AsyncClient):
    company_id = await _create_company(jobs_api_client)
    create_response = await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(description="Full job description"),
    )
    job_id = create_response.json()["id"]

    response = await jobs_api_client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert response.json()["company_id"] == company_id
    assert response.json()["company_name"] == "Jobs Co"
    assert response.json()["company_website_url"] == "jobs-co.example"
    assert response.json()["description"] == "Full job description"


@pytest.mark.asyncio
async def test_get_missing_job_returns_404(jobs_api_client: AsyncClient):
    response = await jobs_api_client.get("/api/v1/jobs/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_job_updates_job_and_normalized_title(
    jobs_api_client: AsyncClient,
):
    company_id = await _create_company(jobs_api_client)
    create_response = await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(),
    )
    job_id = create_response.json()["id"]

    response = await jobs_api_client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Staff ML Engineer"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Staff ML Engineer"
    assert response.json()["normalized_title"] == "staff ml engineer"


@pytest.mark.asyncio
async def test_delete_job_deletes_job(jobs_api_client: AsyncClient):
    company_id = await _create_company(jobs_api_client)
    create_response = await jobs_api_client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json=_job_payload(),
    )
    job_id = create_response.json()["id"]

    delete_response = await jobs_api_client.delete(f"/api/v1/jobs/{job_id}")
    get_response = await jobs_api_client.get(f"/api/v1/jobs/{job_id}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Job deleted successfully"}
    assert get_response.status_code == 404
