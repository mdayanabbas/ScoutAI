from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user_profile import UserProfile


def _empty_list() -> list:
    return []


class JobMatchingProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_matching_profiles"
    __table_args__ = (
        UniqueConstraint("user_profile_id", name="uq_job_matching_profiles_user_profile_id"),
        Index("ix_job_matching_profiles_user_profile_id", "user_profile_id"),
    )

    user_profile_id: Mapped[str] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    matching_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    target_titles_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    target_role_categories_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    preferred_seniority_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    years_of_experience: Mapped[float | None] = mapped_column(Float)
    skills_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    technologies_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    preferred_locations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    preferred_countries_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    accepted_remote_types_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    accepted_employment_types_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    minimum_salary: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str | None] = mapped_column(String(8))
    visa_sponsorship_required: Mapped[bool | None] = mapped_column(Boolean)
    work_authorization_countries_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    willing_to_relocate: Mapped[bool | None] = mapped_column(Boolean)
    preferred_company_stages_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    preferred_company_sizes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    excluded_titles_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    excluded_role_categories_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    excluded_company_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    excluded_locations_json: Mapped[list] = mapped_column(JSON, nullable=False, default=_empty_list)
    notes: Mapped[str | None] = mapped_column(Text)

    user_profile: Mapped["UserProfile"] = relationship(back_populates="job_matching_profile")
