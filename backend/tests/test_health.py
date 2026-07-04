import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_root(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ScoutAI API"
    assert data["environment"] == "local"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_api_v1(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ScoutAI API"
    assert data["environment"] == "local"
    assert data["version"] == "0.1.0"
