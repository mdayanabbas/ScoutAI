from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.company_page import CompanyPage
from app.repositories.base import BaseRepository


class CompanyPageRepository(BaseRepository[CompanyPage]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CompanyPage)

    def get_by_company_and_url(
        self, company_id: str, url: str
    ) -> CompanyPage | None:
        stmt = select(CompanyPage).where(
            CompanyPage.company_id == company_id, CompanyPage.url == url
        )
        return self.session.scalar(stmt)

    def list_by_company(
        self,
        company_id: str,
        offset: int = 0,
        limit: int = 50,
        page_type: str | None = None,
    ) -> list[CompanyPage]:
        stmt = select(CompanyPage).where(CompanyPage.company_id == company_id)
        if page_type is not None:
            stmt = stmt.where(CompanyPage.page_type == page_type)
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_by_company(self, company_id: str, page_type: str | None = None) -> int:
        stmt = select(func.count()).where(CompanyPage.company_id == company_id)
        if page_type is not None:
            stmt = stmt.where(CompanyPage.page_type == page_type)
        stmt = stmt.select_from(CompanyPage)
        return self.session.scalar(stmt) or 0

    def create_page(self, page: CompanyPage) -> CompanyPage:
        return self.create(page)

    def update_page(self, page: CompanyPage, data: dict[str, Any]) -> CompanyPage:
        return self.update(page, data)

    def delete_page(self, page: CompanyPage) -> None:
        self.delete(page)
