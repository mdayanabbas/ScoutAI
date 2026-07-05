from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_step import AgentStep
from app.repositories.base import BaseRepository


class AgentStepRepository(BaseRepository[AgentStep]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AgentStep)

    def list_by_agent_run(self, agent_run_id: str) -> list[AgentStep]:
        stmt = (
            select(AgentStep)
            .where(AgentStep.agent_run_id == agent_run_id)
            .order_by(AgentStep.step_order.asc(), AgentStep.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def create_step(self, agent_step: AgentStep) -> AgentStep:
        return self.create(agent_step)

    def update_step(
        self, agent_step: AgentStep, data: dict[str, Any]
    ) -> AgentStep:
        return self.update(agent_step, data)

    def delete_step(self, agent_step: AgentStep) -> None:
        self.delete(agent_step)
