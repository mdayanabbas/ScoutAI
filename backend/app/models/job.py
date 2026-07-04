from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import JobStatus, RemoteType, RoleCategory

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.company import Company


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String, index=True)
    normalized_title: Mapped[str | None] = mapped_column(String, index=True)
    role_category: Mapped[RoleCategory | None] = mapped_column(
        Enum(
            RoleCategory,
            name="rolecategory",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=RoleCategory.OTHER,
    )
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None]
    remote_type: Mapped[RemoteType | None] = mapped_column(
        Enum(RemoteType, name="remotetype", native_enum=False),
        default=RemoteType.UNKNOWN,
    )
    experience_min: Mapped[int | None] = mapped_column(Integer)
    experience_max: Mapped[int | None] = mapped_column(Integer)
    salary_min: Mapped[int | None] = mapped_column(Numeric)
    salary_max: Mapped[int | None] = mapped_column(Numeric)
    salary_currency: Mapped[str | None] = mapped_column(String)
    job_url: Mapped[str | None]
    source_platform: Mapped[str | None]
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="jobstatus", native_enum=False),
        default=JobStatus.ACTIVE,
    )
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship(back_populates="jobs")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="job")

    __table_args__ = (
        UniqueConstraint("company_id", "job_url"),
        Index("ix_jobs_role_category", "role_category"),
        Index("ix_jobs_remote_type", "remote_type"),
    )
