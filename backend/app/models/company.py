from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.utils.enums import CompanySource, CompanyStage

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.company_page import CompanyPage
    from app.models.crawl_run import CrawlRun
    from app.models.job import Job
    from app.models.tech_stack_item import TechStackItem


class Company(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String, index=True)
    website_url: Mapped[str | None]
    normalized_domain: Mapped[str] = mapped_column(
        String, unique=True, index=True
    )
    description: Mapped[str | None]
    country: Mapped[str | None]
    city: Mapped[str | None]
    stage: Mapped[CompanyStage] = mapped_column(
        Enum(
            CompanyStage,
            name="companystage",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CompanyStage.UNKNOWN,
    )
    source: Mapped[CompanySource] = mapped_column(
        Enum(
            CompanySource,
            name="companysource",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CompanySource.OTHER,
    )
    employee_count_min: Mapped[int | None] = mapped_column(Integer)
    employee_count_max: Mapped[int | None] = mapped_column(Integer)
    founded_year: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company_pages: Mapped[list["CompanyPage"]] = relationship(
        back_populates="company"
    )
    jobs: Mapped[list["Job"]] = relationship(back_populates="company")
    tech_stack_items: Mapped[list["TechStackItem"]] = relationship(
        back_populates="company"
    )
    crawl_runs: Mapped[list["CrawlRun"]] = relationship(back_populates="company")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="company")
