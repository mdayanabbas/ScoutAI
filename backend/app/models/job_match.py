from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.job_matching_profile import JobMatchingProfile


def _empty_list() -> list:
    return []


def _empty_dict() -> dict:
    return {}


class JobMatch(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("job_id", "job_matching_profile_id", name="uq_job_matches_job_profile"),
        Index("ix_job_matches_job_id", "job_id"),
        Index("ix_job_matches_profile_id", "job_matching_profile_id"),
        Index("ix_job_matches_eligibility_status", "eligibility_status"),
        Index("ix_job_matches_remote_eligibility", "remote_eligibility"),
        Index("ix_job_matches_match_tier", "match_tier"),
        Index("ix_job_matches_total_score", "total_score"),
        Index("ix_job_matches_scored_at", "scored_at"),
        Index("ix_job_matches_profile_score", "job_matching_profile_id", "total_score"),
    )

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    job_matching_profile_id: Mapped[str] = mapped_column(
        ForeignKey("job_matching_profiles.id", ondelete="CASCADE"), nullable=False
    )
    eligibility_status: Mapped[str] = mapped_column(String(32), nullable=False)
    eligibility_reason: Mapped[str | None] = mapped_column(String(500))
    remote_eligibility: Mapped[str] = mapped_column(String(64), nullable=False)
    match_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    role_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    seniority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    remote_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    employment_type_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    skills_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    technology_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    salary_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    company_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    hard_filter_reasons_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    positive_signals_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    negative_signals_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    missing_information_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    score_breakdown_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=_empty_dict)
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job: Mapped["Job"] = relationship(back_populates="job_matches")
    job_matching_profile: Mapped["JobMatchingProfile"] = relationship(back_populates="job_matches")
