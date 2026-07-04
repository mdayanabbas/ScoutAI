from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Company)

    def get_by_domain(self, normalized_domain: str) -> Company | None:
        stmt = select(Company).where(Company.normalized_domain == normalized_domain)
        return self.session.scalar(stmt)

    def get_by_website_url(self, website_url: str) -> Company | None:
        stmt = select(Company).where(Company.website_url == website_url)
        return self.session.scalar(stmt)

    def _build_list_query(
        self,
        search: str | None = None,
        source: str | None = None,
        stage: str | None = None,
        is_active: bool | None = None,
    ):
        stmt = select(Company)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(Company.name.ilike(pattern), Company.normalized_domain.ilike(pattern))
            )
        if source is not None:
            stmt = stmt.where(Company.source == source)
        if stage is not None:
            stmt = stmt.where(Company.stage == stage)
        if is_active is not None:
            stmt = stmt.where(Company.is_active.is_(is_active))
        return stmt

    def list_companies(
        self,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        source: str | None = None,
        stage: str | None = None,
        is_active: bool | None = None,
    ) -> list[Company]:
        stmt = self._build_list_query(search, source, stage, is_active)
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_companies(
        self,
        search: str | None = None,
        source: str | None = None,
        stage: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        stmt = self._build_list_query(search, source, stage, is_active)
        stmt = select(func.count()).select_from(stmt.subquery())
        return self.session.scalar(stmt) or 0

    def create_company(self, company: Company) -> Company:
        return self.create(company)

    def update_company(self, company: Company, data: dict[str, Any]) -> Company:
        return self.update(company, data)

    def delete_company(self, company: Company) -> None:
        self.delete(company)
