import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def company_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_company(company_api_client: AsyncClient):
    response = await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Acme AI", "website_url": "https://www.acme.ai/"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["name"] == "Acme AI"
    assert data["website_url"] == "acme.ai"
    assert data["normalized_domain"] == "acme.ai"
    assert data["stage"] == "unknown"
    assert data["source"] == "other"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_duplicate_company_domain_returns_409(company_api_client: AsyncClient):
    payload = {"name": "Acme AI", "website_url": "https://acme.ai"}
    await company_api_client.post("/api/v1/companies", json=payload)

    response = await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Acme Again", "website_url": "http://www.acme.ai/"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_list_companies_returns_paginated_response(
    company_api_client: AsyncClient,
):
    await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Acme AI", "website_url": "https://acme.ai"},
    )

    response = await company_api_client.get("/api/v1/companies")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["has_next"] is False
    assert data["has_prev"] is False
    assert data["items"][0]["name"] == "Acme AI"


@pytest.mark.asyncio
async def test_list_companies_supports_search(company_api_client: AsyncClient):
    await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Acme AI", "website_url": "https://acme.ai"},
    )
    await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Beta Labs", "website_url": "https://beta.example"},
    )

    response = await company_api_client.get("/api/v1/companies?search=acme")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["normalized_domain"] == "acme.ai"


@pytest.mark.asyncio
async def test_get_company_by_id(company_api_client: AsyncClient):
    create_response = await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Acme AI", "website_url": "https://acme.ai"},
    )
    company_id = create_response.json()["id"]

    response = await company_api_client.get(f"/api/v1/companies/{company_id}")

    assert response.status_code == 200
    assert response.json()["id"] == company_id


@pytest.mark.asyncio
async def test_missing_company_returns_404(company_api_client: AsyncClient):
    response = await company_api_client.get("/api/v1/companies/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_company_updates_fields(company_api_client: AsyncClient):
    create_response = await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Acme AI", "website_url": "https://acme.ai"},
    )
    company_id = create_response.json()["id"]

    response = await company_api_client.patch(
        f"/api/v1/companies/{company_id}",
        json={"name": "Acme Intelligence"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Acme Intelligence"


@pytest.mark.asyncio
async def test_patch_website_url_updates_normalized_domain(
    company_api_client: AsyncClient,
):
    create_response = await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Acme AI", "website_url": "https://acme.ai"},
    )
    company_id = create_response.json()["id"]

    response = await company_api_client.patch(
        f"/api/v1/companies/{company_id}",
        json={"website_url": "https://www.new-acme.ai/"},
    )

    assert response.status_code == 200
    assert response.json()["website_url"] == "new-acme.ai"
    assert response.json()["normalized_domain"] == "new-acme.ai"


@pytest.mark.asyncio
async def test_delete_company(company_api_client: AsyncClient):
    create_response = await company_api_client.post(
        "/api/v1/companies",
        json={"name": "Acme AI", "website_url": "https://acme.ai"},
    )
    company_id = create_response.json()["id"]

    delete_response = await company_api_client.delete(
        f"/api/v1/companies/{company_id}"
    )
    get_response = await company_api_client.get(f"/api/v1/companies/{company_id}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Company deleted successfully"}
    assert get_response.status_code == 404
