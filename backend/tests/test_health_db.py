from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.db.session import get_db


@pytest.mark.asyncio
async def test_health_db_returns_ok_when_db_connected(client: AsyncClient):
    response = await client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "database": "connected"}


@pytest.mark.asyncio
async def test_health_root_db_returns_ok_when_db_connected(client: AsyncClient):
    response = await client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "database": "connected"}


@pytest.mark.asyncio
async def test_health_db_returns_error_on_db_failure(client: AsyncClient, app: FastAPI):
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("connection refused")

    def failing_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = failing_get_db
    try:
        response = await client.get("/api/v1/health/db")
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "DATABASE_ERROR"
    finally:
        del app.dependency_overrides[get_db]
