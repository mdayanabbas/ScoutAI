import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db


@pytest.fixture
async def agent_runs_api_client(app, db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _create_company(client: AsyncClient, name: str = "Agent Co") -> str:
    domain = name.lower().replace(" ", "-")
    response = await client.post(
        "/api/v1/companies",
        json={"name": name, "website_url": f"https://{domain}.example"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_job(client: AsyncClient, company_id: str) -> str:
    response = await client.post(
        f"/api/v1/companies/{company_id}/jobs",
        json={
            "title": "AI Engineer",
            "job_url": "https://agent.example/jobs/ai-engineer",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_agent_run(
    client: AsyncClient,
    company_id: str | None = None,
    job_id: str | None = None,
    agent_name: str = "job_understanding_agent",
) -> dict:
    payload = {
        "company_id": company_id,
        "job_id": job_id,
        "agent_name": agent_name,
        "model_provider": "openai",
        "model_name": "gpt-4.1-mini",
        "input_summary": "Parse job description",
        "metadata": {"source": "manual_test"},
    }
    response = await client.post("/api/v1/agent-runs", json=payload)
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_create_agent_run(agent_runs_api_client: AsyncClient):
    company_id = await _create_company(agent_runs_api_client)
    job_id = await _create_job(agent_runs_api_client, company_id)

    response = await agent_runs_api_client.post(
        "/api/v1/agent-runs",
        json={
            "company_id": company_id,
            "job_id": job_id,
            "agent_name": "job_understanding_agent",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["company_id"] == company_id
    assert data["job_id"] == job_id
    assert data["agent_name"] == "job_understanding_agent"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_agent_run_with_missing_company_returns_404(
    agent_runs_api_client: AsyncClient,
):
    response = await agent_runs_api_client.post(
        "/api/v1/agent-runs",
        json={"company_id": "missing", "agent_name": "company_research_agent"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_agent_run_with_missing_job_returns_404(
    agent_runs_api_client: AsyncClient,
):
    response = await agent_runs_api_client.post(
        "/api/v1/agent-runs",
        json={"job_id": "missing", "agent_name": "job_understanding_agent"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_agent_runs_returns_paginated_response(
    agent_runs_api_client: AsyncClient,
):
    agent_run = await _create_agent_run(agent_runs_api_client)

    response = await agent_runs_api_client.get("/api/v1/agent-runs")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["items"][0]["id"] == agent_run["id"]


@pytest.mark.asyncio
async def test_list_agent_runs_supports_filters(agent_runs_api_client: AsyncClient):
    company_id = await _create_company(agent_runs_api_client)
    job_id = await _create_job(agent_runs_api_client, company_id)
    first = await _create_agent_run(
        agent_runs_api_client,
        company_id=company_id,
        job_id=job_id,
        agent_name="job_understanding_agent",
    )
    await _create_agent_run(
        agent_runs_api_client,
        agent_name="company_research_agent",
    )
    await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{first['id']}/mark-running"
    )

    by_name = await agent_runs_api_client.get(
        "/api/v1/agent-runs?agent_name=job_understanding_agent"
    )
    by_status = await agent_runs_api_client.get("/api/v1/agent-runs?status=running")
    by_company = await agent_runs_api_client.get(
        f"/api/v1/agent-runs?company_id={company_id}"
    )
    by_job = await agent_runs_api_client.get(f"/api/v1/agent-runs?job_id={job_id}")

    assert by_name.json()["total"] == 1
    assert by_status.json()["total"] == 1
    assert by_company.json()["items"][0]["company_id"] == company_id
    assert by_job.json()["items"][0]["job_id"] == job_id


@pytest.mark.asyncio
async def test_get_agent_run(agent_runs_api_client: AsyncClient):
    agent_run = await _create_agent_run(agent_runs_api_client)

    response = await agent_runs_api_client.get(f"/api/v1/agent-runs/{agent_run['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == agent_run["id"]


@pytest.mark.asyncio
async def test_get_missing_agent_run_returns_404(agent_runs_api_client: AsyncClient):
    response = await agent_runs_api_client.get("/api/v1/agent-runs/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_mark_running_updates_status(agent_runs_api_client: AsyncClient):
    agent_run = await _create_agent_run(agent_runs_api_client)

    response = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/mark-running"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["started_at"] is not None


@pytest.mark.asyncio
async def test_mark_success_updates_status_and_output(
    agent_runs_api_client: AsyncClient,
):
    agent_run = await _create_agent_run(agent_runs_api_client)

    response = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/mark-success",
        json={"output_summary": "Parsed successfully", "latency_ms": 1200},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["finished_at"] is not None
    assert response.json()["output_summary"] == "Parsed successfully"
    assert response.json()["latency_ms"] == 1200


@pytest.mark.asyncio
async def test_mark_failed_updates_status_and_error(
    agent_runs_api_client: AsyncClient,
):
    agent_run = await _create_agent_run(agent_runs_api_client)

    response = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/mark-failed",
        json={"error_message": "Model returned invalid JSON", "latency_ms": 1500},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["finished_at"] is not None
    assert response.json()["error_message"] == "Model returned invalid JSON"
    assert response.json()["latency_ms"] == 1500


@pytest.mark.asyncio
async def test_add_and_list_agent_steps_ordered(agent_runs_api_client: AsyncClient):
    agent_run = await _create_agent_run(agent_runs_api_client)

    second = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/steps",
        json={"step_name": "second", "step_order": 2},
    )
    first = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/steps",
        json={"step_name": "first", "step_order": 1},
    )
    response = await agent_runs_api_client.get(
        f"/api/v1/agent-runs/{agent_run['id']}/steps"
    )

    assert second.status_code == 201
    assert first.status_code == 201
    assert [step["step_name"] for step in response.json()] == ["first", "second"]


@pytest.mark.asyncio
async def test_patch_agent_step_updates_step(agent_runs_api_client: AsyncClient):
    agent_run = await _create_agent_run(agent_runs_api_client)
    step = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/steps",
        json={"step_name": "parse", "step_order": 1},
    )

    response = await agent_runs_api_client.patch(
        f"/api/v1/agent-steps/{step.json()['id']}",
        json={"latency_ms": 100, "output_payload": {"valid": True}},
    )

    assert response.status_code == 200
    assert response.json()["latency_ms"] == 100
    assert response.json()["output_payload"] == {"valid": True}


@pytest.mark.asyncio
async def test_delete_agent_step_deletes_step(agent_runs_api_client: AsyncClient):
    agent_run = await _create_agent_run(agent_runs_api_client)
    step = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/steps",
        json={"step_name": "parse", "step_order": 1},
    )

    delete_response = await agent_runs_api_client.delete(
        f"/api/v1/agent-steps/{step.json()['id']}"
    )
    list_response = await agent_runs_api_client.get(
        f"/api/v1/agent-runs/{agent_run['id']}/steps"
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Agent step deleted successfully"}
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_negative_latency_returns_validation_error(
    agent_runs_api_client: AsyncClient,
):
    agent_run = await _create_agent_run(agent_runs_api_client)

    response = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/mark-success",
        json={"latency_ms": -1},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_empty_error_message_returns_validation_error(
    agent_runs_api_client: AsyncClient,
):
    agent_run = await _create_agent_run(agent_runs_api_client)

    response = await agent_runs_api_client.post(
        f"/api/v1/agent-runs/{agent_run['id']}/mark-failed",
        json={"error_message": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
