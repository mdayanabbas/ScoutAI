import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def discovery_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_run_manual_discovery_api_returns_candidates_and_evidence(
    discovery_api_client: AsyncClient,
):
    response = await discovery_api_client.post(
        "/api/v1/discovery/manual",
        json={
            "metadata": {"reason": "manual pipeline verification"},
            "candidates": [
                {
                    "source_identifier": "manual-acme-ai",
                    "name": "Acme AI",
                    "website_url": "https://www.acme.ai/",
                    "description": "AI workflow automation.",
                    "evidence": [
                        {
                            "evidence_type": "source_listing",
                            "source_url": "https://example.com/startups/acme-ai",
                            "title": "Acme AI listing",
                            "excerpt": "Acme AI builds workflow automation.",
                        }
                    ],
                    "raw_payload": {"source_note": "manual"},
                }
            ],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["run"]["status"] == "success"
    assert data["run"]["metadata"] == {"reason": "manual pipeline verification"}
    assert data["candidates"][0]["normalized_domain"] == "acme.ai"
    assert data["candidates"][0]["decision"] == "created_company"
    assert data["candidates"][0]["evidence"][0]["source_url"].endswith("acme-ai")


@pytest.mark.asyncio
async def test_list_discovery_runs_paginates(discovery_api_client: AsyncClient):
    await discovery_api_client.post(
        "/api/v1/discovery/manual",
        json={
            "candidates": [
                {
                    "source_identifier": "manual-acme",
                    "name": "Acme AI",
                    "website_url": "https://acme.ai",
                }
            ]
        },
    )

    response = await discovery_api_client.get("/api/v1/discovery/runs")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["items"][0]["source"] == "manual"


@pytest.mark.asyncio
async def test_get_discovery_run_and_candidate(discovery_api_client: AsyncClient):
    create_response = await discovery_api_client.post(
        "/api/v1/discovery/manual",
        json={
            "candidates": [
                {
                    "source_identifier": "manual-acme",
                    "name": "Acme AI",
                    "website_url": "https://acme.ai",
                }
            ]
        },
    )
    body = create_response.json()
    run_id = body["run"]["id"]
    candidate_id = body["candidates"][0]["id"]

    run_response = await discovery_api_client.get(f"/api/v1/discovery/runs/{run_id}")
    candidate_response = await discovery_api_client.get(
        f"/api/v1/discovery/candidates/{candidate_id}"
    )

    assert run_response.status_code == 200
    assert run_response.json()["run"]["id"] == run_id
    assert candidate_response.status_code == 200
    assert candidate_response.json()["id"] == candidate_id


@pytest.mark.asyncio
async def test_missing_discovery_resources_return_404(
    discovery_api_client: AsyncClient,
):
    run_response = await discovery_api_client.get("/api/v1/discovery/runs/missing")
    candidate_response = await discovery_api_client.get(
        "/api/v1/discovery/candidates/missing"
    )

    assert run_response.status_code == 404
    assert candidate_response.status_code == 404
