from typing import TYPE_CHECKING

from sqlalchemy import Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import RemoteType

if TYPE_CHECKING:
    from app.models.job_matching_profile import JobMatchingProfile


class UserProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_profiles"

    display_name: Mapped[str | None]
    target_roles: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    preferred_locations: Mapped[list[str] | None] = mapped_column(
        JSON, default=None
    )
    remote_preference: Mapped[RemoteType | None] = mapped_column(
        Enum(
            RemoteType,
            name="remotetype",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=RemoteType.UNKNOWN,
    )
    years_experience: Mapped[int | None]
    skills: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    strong_skills: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    weak_skills: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    preferred_company_stages: Mapped[list[str] | None] = mapped_column(
        JSON, default=None
    )
    preferred_company_sizes: Mapped[list[str] | None] = mapped_column(
        JSON, default=None
    )
    job_matching_profile: Mapped["JobMatchingProfile | None"] = relationship(
        back_populates="user_profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
