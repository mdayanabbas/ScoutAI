from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Float, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import (
    CompanyEnrichmentDecision,
    CompanyEnrichmentResolver,
    CompanyEnrichmentStatus,
)

if TYPE_CHECKING:
    from app.models.discovery_candidate import DiscoveryCandidate


class CompanyEnrichmentAttempt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "company_enrichment_attempts"
    __table_args__ = (
        Index("ix_company_enrichment_attempts_created_at", "created_at"),
    )

    discovery_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_candidates.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[CompanyEnrichmentStatus] = mapped_column(
        Enum(
            CompanyEnrichmentStatus,
            name="companyenrichmentstatus",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CompanyEnrichmentStatus.PENDING,
        index=True,
    )
    resolver: Mapped[CompanyEnrichmentResolver] = mapped_column(
        Enum(
            CompanyEnrichmentResolver,
            name="companyenrichmentresolver",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        index=True,
    )
    proposed_website_url: Mapped[str | None]
    proposed_domain: Mapped[str | None] = mapped_column(String, index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[CompanyEnrichmentDecision | None] = mapped_column(
        Enum(
            CompanyEnrichmentDecision,
            name="companyenrichmentdecision",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        )
    )
    reason: Mapped[str | None]
    error_message: Mapped[str | None] = mapped_column(Text)
    evidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    discovery_candidate: Mapped["DiscoveryCandidate"] = relationship(
        back_populates="enrichment_attempts"
    )
