from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun


class AgentStep(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_steps"

    agent_run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    step_name: Mapped[str] = mapped_column(String, index=True)
    step_order: Mapped[int | None] = mapped_column(Integer)
    input_payload: Mapped[dict | None] = mapped_column(JSON)
    output_payload: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="steps")
