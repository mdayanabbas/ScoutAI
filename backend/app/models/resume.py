from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user_profile import UserProfile


class Resume(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resumes"
    __table_args__ = (
        Index("ix_resumes_user_profile_id", "user_profile_id"),
        Index("ix_resumes_file_sha256", "file_sha256"),
        Index("ix_resumes_is_active", "is_active"),
        Index("ix_resumes_parse_status", "parse_status"),
        Index("ix_resumes_created_at", "created_at"),
    )

    user_profile_id: Mapped[str] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    parse_error: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsed_summary_json: Mapped[dict | None] = mapped_column(JSON)
    skills_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    technologies_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    projects_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    experience_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    education_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    certifications_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    links_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_profile: Mapped["UserProfile"] = relationship(back_populates="resumes")
