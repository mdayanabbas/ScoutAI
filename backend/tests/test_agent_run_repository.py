from app.models.agent_run import AgentRun
from app.models.agent_step import AgentStep
from app.models.company import Company
from app.models.job import Job
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_step_repository import AgentStepRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.utils.enums import AgentRunStatus


def test_agent_run_repository_create_list_and_status_transitions(db_session):
    company = CompanyRepository(db_session).create_company(
        Company(name="Agent Co", normalized_domain="agent.example")
    )
    job = JobRepository(db_session).create_job(
        Job(
            company_id=company.id,
            title="Backend Engineer",
            normalized_title="backend engineer",
            job_url="https://agent.example/jobs/backend",
        )
    )
    repo = AgentRunRepository(db_session)
    agent_run = repo.create_agent_run(
        AgentRun(
            company_id=company.id,
            job_id=job.id,
            agent_name="job_understanding",
            status=AgentRunStatus.PENDING,
        )
    )

    assert repo.get_by_id(agent_run.id) == agent_run
    assert repo.list_by_company(company.id) == [agent_run]
    assert repo.list_by_job(job.id) == [agent_run]
    assert repo.list_recent(agent_name="job_understanding", status=AgentRunStatus.PENDING) == [agent_run]

    repo.mark_running(agent_run)
    assert agent_run.status == AgentRunStatus.RUNNING
    assert agent_run.started_at is not None

    repo.mark_success(agent_run, output_summary="parsed", latency_ms=42)
    assert agent_run.status == AgentRunStatus.SUCCESS
    assert agent_run.output_summary == "parsed"
    assert agent_run.latency_ms == 42

    repo.mark_failed(agent_run, "model error", latency_ms=84)
    assert agent_run.status == AgentRunStatus.FAILED
    assert agent_run.error_message == "model error"
    assert agent_run.latency_ms == 84


def test_agent_step_repository_create_list_update_delete(db_session):
    agent_run = AgentRunRepository(db_session).create_agent_run(
        AgentRun(agent_name="company_research", status=AgentRunStatus.PENDING)
    )
    repo = AgentStepRepository(db_session)
    step = repo.create_step(
        AgentStep(agent_run_id=agent_run.id, step_name="summarize", step_order=1)
    )

    assert repo.get_by_id(step.id) == step
    assert repo.list_by_agent_run(agent_run.id) == [step]

    repo.update_step(step, {"latency_ms": 7})
    assert repo.get_by_id(step.id).latency_ms == 7

    repo.delete_step(step)
    assert repo.list_by_agent_run(agent_run.id) == []
