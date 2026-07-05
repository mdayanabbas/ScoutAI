import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def company_pages_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _create_company(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/companies",
        json={"name": "Pages Co", "website_url": "https://pages.example"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _page_payload(**overrides) -> dict:
    payload = {
        "url": "https://www.pages.example/about/",
        "page_type": "about",
        "title": "About Pages Co",
        "raw_text": "Full page text",
        "status_code": 200,
        "content_length": 1234,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_create_company_page(company_pages_api_client: AsyncClient):
    company_id = await _create_company(company_pages_api_client)

    response = await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["company_id"] == company_id
    assert data["url"] == "pages.example/about"
    assert data["page_type"] == "about"
    assert data["title"] == "About Pages Co"
    assert data["status_code"] == 200
    assert data["content_length"] == 1234


@pytest.mark.asyncio
async def test_create_same_page_updates_existing_page(
    company_pages_api_client: AsyncClient,
):
    company_id = await _create_company(company_pages_api_client)
    first = await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(),
    )

    second = await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(title="Updated About", raw_text="Updated text"),
    )

    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["title"] == "Updated About"

    list_response = await company_pages_api_client.get(
        f"/api/v1/companies/{company_id}/pages"
    )
    assert list_response.json()["total"] == 1


@pytest.mark.asyncio
async def test_create_page_with_missing_company_returns_404(
    company_pages_api_client: AsyncClient,
):
    response = await company_pages_api_client.post(
        "/api/v1/companies/missing/pages",
        json=_page_payload(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_company_pages_returns_paginated_response(
    company_pages_api_client: AsyncClient,
):
    company_id = await _create_company(company_pages_api_client)
    await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(),
    )

    response = await company_pages_api_client.get(
        f"/api/v1/companies/{company_id}/pages"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["has_next"] is False
    assert data["has_prev"] is False
    assert data["items"][0]["title"] == "About Pages Co"
    assert "raw_text" not in data["items"][0]


@pytest.mark.asyncio
async def test_list_company_pages_supports_page_type_filter(
    company_pages_api_client: AsyncClient,
):
    company_id = await _create_company(company_pages_api_client)
    await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(page_type="about"),
    )
    await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(
            url="https://pages.example/careers",
            page_type="careers",
            title="Careers",
        ),
    )

    response = await company_pages_api_client.get(
        f"/api/v1/companies/{company_id}/pages?page_type=careers"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["page_type"] == "careers"


@pytest.mark.asyncio
async def test_get_company_page_returns_full_page(
    company_pages_api_client: AsyncClient,
):
    company_id = await _create_company(company_pages_api_client)
    create_response = await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(raw_text="Full text here"),
    )
    page_id = create_response.json()["id"]

    response = await company_pages_api_client.get(f"/api/v1/company-pages/{page_id}")

    assert response.status_code == 200
    assert response.json()["id"] == page_id
    assert response.json()["raw_text"] == "Full text here"


@pytest.mark.asyncio
async def test_get_missing_company_page_returns_404(
    company_pages_api_client: AsyncClient,
):
    response = await company_pages_api_client.get("/api/v1/company-pages/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_company_page_updates_page(
    company_pages_api_client: AsyncClient,
):
    company_id = await _create_company(company_pages_api_client)
    create_response = await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(),
    )
    page_id = create_response.json()["id"]

    response = await company_pages_api_client.patch(
        f"/api/v1/company-pages/{page_id}",
        json={"title": "Patched About", "url": "https://pages.example/company"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Patched About"
    assert response.json()["url"] == "pages.example/company"


@pytest.mark.asyncio
async def test_delete_company_page_deletes_page(
    company_pages_api_client: AsyncClient,
):
    company_id = await _create_company(company_pages_api_client)
    create_response = await company_pages_api_client.post(
        f"/api/v1/companies/{company_id}/pages",
        json=_page_payload(),
    )
    page_id = create_response.json()["id"]

    delete_response = await company_pages_api_client.delete(
        f"/api/v1/company-pages/{page_id}"
    )
    get_response = await company_pages_api_client.get(
        f"/api/v1/company-pages/{page_id}"
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "message": "Company page deleted successfully"
    }
    assert get_response.status_code == 404
