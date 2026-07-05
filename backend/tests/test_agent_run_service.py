import pytest

from app.core.errors import NotFoundError
from app.services.agent_run_service import AgentRunService
from app.services.company_service import CompanyService
from app.services.job_service import JobService
from app.utils.enums import AgentRunStatus


def test_agent_run_status_transitions_and_step_creation(db_session):
    company = CompanyService(db_session).create_company(
        {"name": "Agent Co", "website_url": "https://agent.example"}
    )
    job = JobService(db_session).create_or_update_job(
        company.id,
        {"title": "AI Engineer", "job_url": "https://agent.example/jobs/ai"},
    )
    service = AgentRunService(db_session)
    agent_run = service.create_agent_run(
        {
            "company_id": company.id,
            "job_id": job.id,
            "agent_name": "job_understanding",
        }
    )

    assert agent_run.status == AgentRunStatus.PENDING
    assert service.list_company_runs(company.id) == [agent_run]
    assert service.list_job_runs(job.id) == [agent_run]

    running = service.mark_running(agent_run.id)
    assert running.status == AgentRunStatus.RUNNING

    success = service.mark_success(agent_run.id, output_summary="ok", latency_ms=10)
    assert success.status == AgentRunStatus.SUCCESS
    assert success.output_summary == "ok"
    assert success.latency_ms == 10

    step = service.add_step(
        agent_run.id,
        {"step_name": "parse", "step_order": 1, "output_payload": {"ok": True}},
    )
    assert service.list_steps(agent_run.id) == [step]

    failed = service.mark_failed(agent_run.id, "error", latency_ms=20)
    assert failed.status == AgentRunStatus.FAILED
    assert failed.error_message == "error"
    assert failed.latency_ms == 20


def test_agent_run_missing_refs_raise_not_found(db_session):
    service = AgentRunService(db_session)

    with pytest.raises(NotFoundError):
        service.create_agent_run(
            {"company_id": "missing", "agent_name": "company_research"}
        )

    with pytest.raises(NotFoundError):
        service.add_step("missing", {"step_name": "parse"})
