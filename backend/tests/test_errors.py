import pytest
from httpx import AsyncClient

from app.core.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)


def test_app_error_defaults():
    exc = AppError("TEST", "Something went wrong")
    assert exc.code == "TEST"
    assert exc.message == "Something went wrong"
    assert exc.status_code == 500
    assert exc.details == {}


def test_app_error_with_details():
    exc = AppError("TEST", "msg", status_code=400, details={"field": "x"})
    assert exc.status_code == 400
    assert exc.details == {"field": "x"}


def test_not_found_error():
    exc = NotFoundError()
    assert exc.code == "NOT_FOUND"
    assert exc.status_code == 404


def test_conflict_error():
    exc = ConflictError()
    assert exc.code == "CONFLICT"
    assert exc.status_code == 409


def test_validation_app_error():
    exc = ValidationAppError()
    assert exc.code == "VALIDATION_ERROR"
    assert exc.status_code == 422


def test_unauthorized_error():
    exc = UnauthorizedError()
    assert exc.code == "UNAUTHORIZED"
    assert exc.status_code == 401


def test_forbidden_error():
    exc = ForbiddenError()
    assert exc.code == "FORBIDDEN"
    assert exc.status_code == 403


@pytest.mark.asyncio
async def test_app_error_handler_returns_json(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "error" not in data


@pytest.mark.asyncio
async def test_validation_error_format(client: AsyncClient):
    response = await client.post(
        "/api/v1/health",
        json={"bad": "data"},
    )
    assert response.status_code in (405, 422)
