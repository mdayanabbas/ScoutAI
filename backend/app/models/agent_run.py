from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import AgentRunStatus

if TYPE_CHECKING:
    from app.models.agent_step import AgentStep
    from app.models.company import Company
    from app.models.job import Job


class AgentRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    company_id: Mapped[str | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(
            AgentRunStatus,
            name="agentrunstatus",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AgentRunStatus.PENDING,
    )
    model_provider: Mapped[str | None]
    model_name: Mapped[str | None]
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company | None"] = relationship(back_populates="agent_runs")
    job: Mapped["Job | None"] = relationship(back_populates="agent_runs")
    steps: Mapped[list["AgentStep"]] = relationship(
        back_populates="agent_run"
    )

    __table_args__ = (
        Index("ix_agent_runs_status", "status"),
        Index("ix_agent_runs_company_id", "company_id"),
        Index("ix_agent_runs_job_id", "job_id"),
    )
