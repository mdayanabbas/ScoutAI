from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.discovery_candidate import DiscoveryCandidate


class DiscoveryEvidence(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "discovery_evidence"

    discovery_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_candidates.id", ondelete="CASCADE"), index=True
    )
    evidence_type: Mapped[str] = mapped_column(String, index=True)
    source_url: Mapped[str]
    title: Mapped[str | None]
    excerpt: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    candidate: Mapped["DiscoveryCandidate"] = relationship(back_populates="evidence")
