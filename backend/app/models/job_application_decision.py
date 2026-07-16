from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.user_profile import UserProfile


class JobApplicationDecision(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_application_decisions"
    __table_args__ = (
        UniqueConstraint("job_id", "user_profile_id", name="uq_job_application_decisions_job_user"),
        Index("ix_job_application_decisions_job_id", "job_id"),
        Index("ix_job_application_decisions_user_profile_id", "user_profile_id"),
        Index("ix_job_application_decisions_status", "status"),
    )

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    user_profile_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="interested")
    notes: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job: Mapped["Job"] = relationship(back_populates="application_decisions")
    user_profile: Mapped["UserProfile"] = relationship(back_populates="job_application_decisions")
