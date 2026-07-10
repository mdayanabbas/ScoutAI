from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.discovery_candidate import DiscoveryCandidate
    from app.models.job import Job


class JobDiscoveryLink(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_discovery_links"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "discovery_candidate_id",
            name="uq_job_discovery_links_job_candidate",
        ),
        Index("ix_job_discovery_links_job_id", "job_id"),
        Index("ix_job_discovery_links_discovery_candidate_id", "discovery_candidate_id"),
        Index("ix_job_discovery_links_created_at", "created_at"),
    )

    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE")
    )
    discovery_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_candidates.id", ondelete="CASCADE")
    )

    job: Mapped["Job"] = relationship(back_populates="discovery_links")
    discovery_candidate: Mapped["DiscoveryCandidate"] = relationship()
