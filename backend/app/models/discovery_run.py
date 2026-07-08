from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, Index, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import DiscoveryRunStatus, DiscoverySource

if TYPE_CHECKING:
    from app.models.discovery_candidate import DiscoveryCandidate


class DiscoveryRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "discovery_runs"
    __table_args__ = (Index("ix_discovery_runs_created_at", "created_at"),)

    source: Mapped[DiscoverySource] = mapped_column(
        Enum(
            DiscoverySource,
            name="discoverysource",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        index=True,
    )
    status: Mapped[DiscoveryRunStatus] = mapped_column(
        Enum(
            DiscoveryRunStatus,
            name="discoveryrunstatus",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DiscoveryRunStatus.PENDING,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    candidates_found: Mapped[int] = mapped_column(Integer, default=0)
    candidates_normalized: Mapped[int] = mapped_column(Integer, default=0)
    companies_created: Mapped[int] = mapped_column(Integer, default=0)
    companies_matched: Mapped[int] = mapped_column(Integer, default=0)
    candidates_rejected: Mapped[int] = mapped_column(Integer, default=0)
    candidates_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    candidates: Mapped[list["DiscoveryCandidate"]] = relationship(
        back_populates="discovery_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
