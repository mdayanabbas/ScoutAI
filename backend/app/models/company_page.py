from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import PageType

if TYPE_CHECKING:
    from app.models.company import Company


class CompanyPage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "company_pages"

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str]
    page_type: Mapped[PageType] = mapped_column(
        Enum(
            PageType,
            name="pagetype",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PageType.UNKNOWN,
    )
    title: Mapped[str | None] = mapped_column(String)
    raw_text: Mapped[str | None] = mapped_column(Text)
    html_hash: Mapped[str | None] = mapped_column(String)
    status_code: Mapped[int | None]
    content_length: Mapped[int | None]
    last_crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    company: Mapped["Company"] = relationship(back_populates="company_pages")

    __table_args__ = (
        UniqueConstraint("company_id", "url"),
        Index("ix_company_pages_page_type", "page_type"),
    )
