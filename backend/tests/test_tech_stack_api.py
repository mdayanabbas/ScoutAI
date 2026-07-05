import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def tech_stack_api_client(app, db_session):
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
        json={"name": "Stack Co", "website_url": "https://stack.example"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _tech_item_payload(**overrides) -> dict:
    payload = {
        "name": " FastAPI ",
        "category": "backend_framework",
        "source": "manual",
        "confidence": 0.95,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_create_tech_stack_item(tech_stack_api_client: AsyncClient):
    company_id = await _create_company(tech_stack_api_client)

    response = await tech_stack_api_client.post(
        f"/api/v1/companies/{company_id}/tech-stack",
        json=_tech_item_payload(),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["company_id"] == company_id
    assert data["name"] == "FastAPI"
    assert data["category"] == "backend_framework"
    assert data["source"] == "manual"
    assert data["confidence"] == 0.95


@pytest.mark.asyncio
async def test_create_same_tech_stack_item_updates_existing_item(
    tech_stack_api_client: AsyncClient,
):
    company_id = await _create_company(tech_stack_api_client)
    first = await tech_stack_api_client.post(
        f"/api/v1/companies/{company_id}/tech-stack",
        json=_tech_item_payload(),
    )

    second = await tech_stack_api_client.post(
        f"/api/v1/companies/{company_id}/tech-stack",
        json=_tech_item_payload(confidence=0.8, category="api_framework"),
    )

    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["category"] == "api_framework"
    assert second.json()["confidence"] == 0.8

    list_response = await tech_stack_api_client.get(
        f"/api/v1/companies/{company_id}/tech-stack"
    )
    assert len(list_response.json()) == 1


@pytest.mark.asyncio
async def test_create_tech_stack_item_with_missing_company_returns_404(
    tech_stack_api_client: AsyncClient,
):
    response = await tech_stack_api_client.post(
        "/api/v1/companies/missing/tech-stack",
        json=_tech_item_payload(),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_company_tech_stack_returns_items(
    tech_stack_api_client: AsyncClient,
):
    company_id = await _create_company(tech_stack_api_client)
    await tech_stack_api_client.post(
        f"/api/v1/companies/{company_id}/tech-stack",
        json=_tech_item_payload(name="Python"),
    )
    await tech_stack_api_client.post(
        f"/api/v1/companies/{company_id}/tech-stack",
        json=_tech_item_payload(name="FastAPI"),
    )

    response = await tech_stack_api_client.get(
        f"/api/v1/companies/{company_id}/tech-stack"
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["FastAPI", "Python"]


@pytest.mark.asyncio
async def test_list_company_tech_stack_with_missing_company_returns_404(
    tech_stack_api_client: AsyncClient,
):
    response = await tech_stack_api_client.get(
        "/api/v1/companies/missing/tech-stack"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_tech_stack_item_updates_item(
    tech_stack_api_client: AsyncClient,
):
    company_id = await _create_company(tech_stack_api_client)
    create_response = await tech_stack_api_client.post(
        f"/api/v1/companies/{company_id}/tech-stack",
        json=_tech_item_payload(),
    )
    item_id = create_response.json()["id"]

    response = await tech_stack_api_client.patch(
        f"/api/v1/tech-stack/{item_id}",
        json={"name": " Starlette ", "confidence": 0.7},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Starlette"
    assert response.json()["confidence"] == 0.7


@pytest.mark.asyncio
async def test_patch_missing_tech_stack_item_returns_404(
    tech_stack_api_client: AsyncClient,
):
    response = await tech_stack_api_client.patch(
        "/api/v1/tech-stack/missing",
        json={"confidence": 0.5},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_tech_stack_item_deletes_item(
    tech_stack_api_client: AsyncClient,
):
    company_id = await _create_company(tech_stack_api_client)
    create_response = await tech_stack_api_client.post(
        f"/api/v1/companies/{company_id}/tech-stack",
        json=_tech_item_payload(),
    )
    item_id = create_response.json()["id"]

    delete_response = await tech_stack_api_client.delete(
        f"/api/v1/tech-stack/{item_id}"
    )
    list_response = await tech_stack_api_client.get(
        f"/api/v1/companies/{company_id}/tech-stack"
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "message": "Tech stack item deleted successfully"
    }
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_invalid_confidence_returns_validation_error(
    tech_stack_api_client: AsyncClient,
):
    company_id = await _create_company(tech_stack_api_client)

    response = await tech_stack_api_client.post(
        f"/api/v1/companies/{company_id}/tech-stack",
        json=_tech_item_payload(confidence=1.5),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
