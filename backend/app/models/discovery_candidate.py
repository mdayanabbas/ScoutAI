from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import (
    DiscoveryCandidateStatus,
    DiscoveryDecision,
    DiscoverySource,
)

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.discovery_evidence import DiscoveryEvidence
    from app.models.discovery_run import DiscoveryRun


class DiscoveryCandidate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "discovery_candidates"
    __table_args__ = (
        UniqueConstraint(
            "discovery_run_id",
            "source",
            "source_identifier",
            name="uq_discovery_candidate_run_source_identifier",
        ),
    )

    discovery_run_id: Mapped[str] = mapped_column(
        ForeignKey("discovery_runs.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[DiscoverySource] = mapped_column(
        Enum(
            DiscoverySource,
            name="discoverysource",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        )
    )
    source_identifier: Mapped[str] = mapped_column(String, index=True)
    raw_name: Mapped[str]
    raw_website_url: Mapped[str | None]
    raw_description: Mapped[str | None] = mapped_column(Text)
    raw_country: Mapped[str | None]
    normalized_name: Mapped[str | None]
    normalized_website_url: Mapped[str | None]
    normalized_domain: Mapped[str | None] = mapped_column(String, index=True)
    normalized_description: Mapped[str | None] = mapped_column(Text)
    normalized_country: Mapped[str | None]
    status: Mapped[DiscoveryCandidateStatus] = mapped_column(
        Enum(
            DiscoveryCandidateStatus,
            name="discoverycandidatestatus",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DiscoveryCandidateStatus.DISCOVERED,
        index=True,
    )
    decision: Mapped[DiscoveryDecision | None] = mapped_column(
        Enum(
            DiscoveryDecision,
            name="discoverydecision",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        )
    )
    rejection_reason: Mapped[str | None]
    error_message: Mapped[str | None] = mapped_column(Text)
    matched_company_id: Mapped[str | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL")
    )
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    discovery_run: Mapped["DiscoveryRun"] = relationship(back_populates="candidates")
    evidence: Mapped[list["DiscoveryEvidence"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    matched_company: Mapped["Company | None"] = relationship()
