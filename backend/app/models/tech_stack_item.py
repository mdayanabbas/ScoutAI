from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.company import Company


class TechStackItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tech_stack_items"

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str | None] = mapped_column(String)
    source: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    company: Mapped["Company"] = relationship(back_populates="tech_stack_items")

    __table_args__ = (
        UniqueConstraint("company_id", "name", "source"),
        Index("ix_tech_stack_items_company_id", "company_id"),
    )
