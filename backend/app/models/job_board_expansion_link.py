from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.discovery_candidate import DiscoveryCandidate
    from app.models.job import Job


class JobBoardExpansionLink(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_board_expansion_links"
    __table_args__ = (
        UniqueConstraint(
            "parent_job_id",
            "child_job_id",
            name="uq_job_board_expansion_links_parent_child",
        ),
        CheckConstraint("parent_job_id <> child_job_id", name="ck_job_board_expansion_links_not_self"),
        Index("ix_job_board_expansion_links_parent_job_id", "parent_job_id"),
        Index("ix_job_board_expansion_links_child_job_id", "child_job_id"),
        Index(
            "ix_job_board_expansion_links_discovery_candidate_id",
            "discovery_candidate_id",
        ),
        Index("ix_job_board_expansion_links_created_at", "created_at"),
    )

    parent_job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE")
    )
    child_job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE")
    )
    discovery_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovery_candidates.id", ondelete="SET NULL")
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)

    parent_job: Mapped["Job"] = relationship(
        foreign_keys=[parent_job_id],
        back_populates="expanded_child_links",
    )
    child_job: Mapped["Job"] = relationship(
        foreign_keys=[child_job_id],
        back_populates="expanded_parent_links",
    )
    discovery_candidate: Mapped["DiscoveryCandidate | None"] = relationship()
