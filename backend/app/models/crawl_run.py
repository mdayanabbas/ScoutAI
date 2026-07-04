from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import CrawlStatus

if TYPE_CHECKING:
    from app.models.company import Company


class CrawlRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "crawl_runs"

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[CrawlStatus] = mapped_column(
        Enum(
            CrawlStatus,
            name="crawlstatus",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CrawlStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pages_found: Mapped[int | None] = mapped_column(Integer)
    pages_crawled: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)

    company: Mapped["Company"] = relationship(back_populates="crawl_runs")

    __table_args__ = (
        Index("ix_crawl_runs_company_id", "company_id"),
        Index("ix_crawl_runs_status", "status"),
    )
