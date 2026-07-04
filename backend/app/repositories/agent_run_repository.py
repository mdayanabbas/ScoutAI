from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.repositories.base import BaseRepository
from app.utils.enums import AgentRunStatus


class AgentRunRepository(BaseRepository[AgentRun]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AgentRun)

    def list_recent(
        self,
        offset: int = 0,
        limit: int = 50,
        agent_name: str | None = None,
        status: str | None = None,
    ) -> list[AgentRun]:
        stmt = select(AgentRun)
        if agent_name is not None:
            stmt = stmt.where(AgentRun.agent_name == agent_name)
        if status is not None:
            stmt = stmt.where(AgentRun.status == status)
        stmt = stmt.order_by(AgentRun.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_by_company(
        self, company_id: str, offset: int = 0, limit: int = 50
    ) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.company_id == company_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_by_job(
        self, job_id: str, offset: int = 0, limit: int = 50
    ) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.job_id == job_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def create_agent_run(self, agent_run: AgentRun) -> AgentRun:
        return self.create(agent_run)

    def update_agent_run(
        self, agent_run: AgentRun, data: dict[str, Any]
    ) -> AgentRun:
        return self.update(agent_run, data)

    def mark_running(self, agent_run: AgentRun) -> AgentRun:
        agent_run.status = AgentRunStatus.RUNNING
        agent_run.started_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(agent_run)
        return agent_run

    def mark_success(
        self,
        agent_run: AgentRun,
        output_summary: str | None = None,
        latency_ms: int | None = None,
    ) -> AgentRun:
        agent_run.status = AgentRunStatus.SUCCESS
        agent_run.finished_at = datetime.now(timezone.utc)
        if output_summary is not None:
            agent_run.output_summary = output_summary
        if latency_ms is not None:
            agent_run.latency_ms = latency_ms
        self.session.commit()
        self.session.refresh(agent_run)
        return agent_run

    def mark_failed(
        self,
        agent_run: AgentRun,
        error_message: str,
        latency_ms: int | None = None,
    ) -> AgentRun:
        agent_run.status = AgentRunStatus.FAILED
        agent_run.finished_at = datetime.now(timezone.utc)
        agent_run.error_message = error_message
        if latency_ms is not None:
            agent_run.latency_ms = latency_ms
        self.session.commit()
        self.session.refresh(agent_run)
        return agent_run
