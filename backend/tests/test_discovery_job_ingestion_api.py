import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def discovery_job_ingestion_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_missing_candidate_returns_404(
    discovery_job_ingestion_api_client: AsyncClient,
):
    response = await discovery_job_ingestion_api_client.post(
        "/api/v1/discovery/candidates/missing/ingest-job"
    )

    assert response.status_code == 404
