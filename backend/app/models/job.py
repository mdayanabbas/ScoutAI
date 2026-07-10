from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    JSON,
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
    from app.models.discovery_candidate import DiscoveryCandidate
    from app.models.job_enrichment_attempt import JobEnrichmentAttempt
    from app.models.job_discovery_link import JobDiscoveryLink


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    discovery_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovery_candidates.id", ondelete="SET NULL"),
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String, index=True)
    normalized_title: Mapped[str | None] = mapped_column(String, index=True)
    role_category: Mapped[RoleCategory | None] = mapped_column(
        Enum(
            RoleCategory,
            name="rolecategory",
            native_enum=False,
            length=64,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=RoleCategory.OTHER,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None]
    remote_type: Mapped[RemoteType | None] = mapped_column(
        Enum(
            RemoteType,
            name="remotetype",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=RemoteType.UNKNOWN,
        index=True,
    )
    experience_min: Mapped[int | None] = mapped_column(Integer)
    experience_max: Mapped[int | None] = mapped_column(Integer)
    salary_min: Mapped[int | None] = mapped_column(Numeric)
    salary_max: Mapped[int | None] = mapped_column(Numeric)
    salary_currency: Mapped[str | None] = mapped_column(String)
    job_url: Mapped[str | None]
    source_platform: Mapped[str | None]
    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus,
            name="jobstatus",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=JobStatus.ACTIVE,
    )
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seniority: Mapped[str | None] = mapped_column(String(64))
    employment_type: Mapped[str | None] = mapped_column(String(64))
    apply_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    salary_text: Mapped[str | None] = mapped_column(Text)
    equity_mentioned: Mapped[bool | None] = mapped_column(Boolean)
    visa_sponsorship: Mapped[str | None] = mapped_column(String(64))
    work_authorization: Mapped[str | None] = mapped_column(Text)
    required_skills_json: Mapped[list[str] | None] = mapped_column(JSON)
    preferred_skills_json: Mapped[list[str] | None] = mapped_column(JSON)
    technologies_json: Mapped[list[str] | None] = mapped_column(JSON)
    enrichment_status: Mapped[str] = mapped_column(
        String(32), default="not_enriched", nullable=False, index=True
    )
    enrichment_confidence: Mapped[float | None] = mapped_column(Float)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship(back_populates="jobs")
    discovery_candidate: Mapped["DiscoveryCandidate | None"] = relationship()
    discovery_links: Mapped[list["JobDiscoveryLink"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    enrichment_attempts: Mapped[list["JobEnrichmentAttempt"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="job")

    __table_args__ = (UniqueConstraint("company_id", "job_url"),)
