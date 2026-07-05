from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.agent_run import AgentRun
from app.models.agent_step import AgentStep
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_step_repository import AgentStepRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.utils.enums import AgentRunStatus


def _data_to_dict(data: Any) -> dict[str, Any]:
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    return dict(data)


def _map_metadata_field(values: dict[str, Any]) -> dict[str, Any]:
    if "metadata" in values:
        values["metadata_json"] = values.pop("metadata")
    return values


class AgentRunService:
    def __init__(self, session: Session) -> None:
        self.company_repository = CompanyRepository(session)
        self.job_repository = JobRepository(session)
        self.run_repository = AgentRunRepository(session)
        self.step_repository = AgentStepRepository(session)

    def _require_agent_run(self, agent_run_id: str) -> AgentRun:
        agent_run = self.run_repository.get_by_id(agent_run_id)
        if agent_run is None:
            raise NotFoundError("Agent run not found")
        return agent_run

    def _validate_refs(self, data: dict[str, Any]) -> None:
        company_id = data.get("company_id")
        if company_id is not None and self.company_repository.get_by_id(company_id) is None:
            raise NotFoundError("Company not found")

        job_id = data.get("job_id")
        if job_id is not None and self.job_repository.get_by_id(job_id) is None:
            raise NotFoundError("Job not found")

    def create_agent_run(self, data: Any) -> AgentRun:
        values = _map_metadata_field(_data_to_dict(data))
        self._validate_refs(values)
        values.setdefault("status", AgentRunStatus.PENDING)
        return self.run_repository.create_agent_run(AgentRun(**values))

    def get_agent_run(self, agent_run_id: str) -> AgentRun:
        return self._require_agent_run(agent_run_id)

    def mark_running(self, agent_run_id: str) -> AgentRun:
        return self.run_repository.mark_running(self._require_agent_run(agent_run_id))

    def mark_success(
        self,
        agent_run_id: str,
        output_summary: str | None = None,
        latency_ms: int | None = None,
    ) -> AgentRun:
        return self.run_repository.mark_success(
            self._require_agent_run(agent_run_id),
            output_summary=output_summary,
            latency_ms=latency_ms,
        )

    def mark_failed(
        self,
        agent_run_id: str,
        error_message: str,
        latency_ms: int | None = None,
    ) -> AgentRun:
        return self.run_repository.mark_failed(
            self._require_agent_run(agent_run_id),
            error_message=error_message,
            latency_ms=latency_ms,
        )

    def add_step(self, agent_run_id: str, data: Any) -> AgentStep:
        self._require_agent_run(agent_run_id)
        values = _data_to_dict(data)
        values["agent_run_id"] = agent_run_id
        return self.step_repository.create_step(AgentStep(**values))

    def list_steps(self, agent_run_id: str) -> list[AgentStep]:
        self._require_agent_run(agent_run_id)
        return self.step_repository.list_by_agent_run(agent_run_id)

    def list_recent_runs(
        self,
        offset: int = 0,
        limit: int = 50,
        agent_name: str | None = None,
        status: str | None = None,
    ) -> list[AgentRun]:
        return self.run_repository.list_recent(
            offset=offset, limit=limit, agent_name=agent_name, status=status
        )

    def list_company_runs(
        self,
        company_id: str,
        offset: int = 0,
        limit: int = 50,
        agent_name: str | None = None,
        status: str | None = None,
    ) -> list[AgentRun]:
        if self.company_repository.get_by_id(company_id) is None:
            raise NotFoundError("Company not found")
        return self.run_repository.list_by_company(
            company_id,
            offset=offset,
            limit=limit,
            agent_name=agent_name,
            status=status,
        )

    def list_job_runs(
        self,
        job_id: str,
        offset: int = 0,
        limit: int = 50,
        agent_name: str | None = None,
        status: str | None = None,
    ) -> list[AgentRun]:
        if self.job_repository.get_by_id(job_id) is None:
            raise NotFoundError("Job not found")
        return self.run_repository.list_by_job(
            job_id,
            offset=offset,
            limit=limit,
            agent_name=agent_name,
            status=status,
        )

    def count_runs(
        self,
        agent_name: str | None = None,
        status: str | None = None,
        company_id: str | None = None,
        job_id: str | None = None,
    ) -> int:
        if company_id is not None and self.company_repository.get_by_id(company_id) is None:
            raise NotFoundError("Company not found")
        if job_id is not None and self.job_repository.get_by_id(job_id) is None:
            raise NotFoundError("Job not found")
        return self.run_repository.count_runs(
            agent_name=agent_name,
            status=status,
            company_id=company_id,
            job_id=job_id,
        )

    def get_step(self, agent_step_id: str) -> AgentStep:
        step = self.step_repository.get_by_id(agent_step_id)
        if step is None:
            raise NotFoundError("Agent step not found")
        return step

    def update_step(self, agent_step_id: str, data: Any) -> AgentStep:
        return self.step_repository.update_step(
            self.get_step(agent_step_id), _data_to_dict(data)
        )

    def delete_step(self, agent_step_id: str) -> None:
        self.step_repository.delete_step(self.get_step(agent_step_id))
