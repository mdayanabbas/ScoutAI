from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company


class CompanyWatchlistItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "company_watchlist_items"
    __table_args__ = (
        Index("ix_company_watchlist_items_company_id", "company_id"),
        Index("ix_company_watchlist_items_normalized_company_name", "normalized_company_name"),
        Index("ix_company_watchlist_items_normalized_domain", "normalized_domain"),
        Index("ix_company_watchlist_items_watch_status", "watch_status"),
        Index("ix_company_watchlist_items_priority", "priority"),
        Index("ix_company_watchlist_items_created_at", "created_at"),
        Index("ix_company_watchlist_items_updated_at", "updated_at"),
    )

    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str | None] = mapped_column(String(255))
    company_url: Mapped[str | None] = mapped_column(Text)
    normalized_company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_domain: Mapped[str | None] = mapped_column(String(255))
    watch_status: Mapped[str] = mapped_column(String(32), nullable=False, default="watching")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    interest_reason: Mapped[str | None] = mapped_column(Text)
    target_roles_json: Mapped[list[str] | None] = mapped_column(JSON)
    preferred_locations_json: Mapped[list[str] | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    tags_json: Mapped[list[str] | None] = mapped_column(JSON)
    remote_interest: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    junior_friendliness_signal: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_job_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company | None"] = relationship()

