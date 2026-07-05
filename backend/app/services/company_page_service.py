from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.company_page import CompanyPage
from app.repositories.company_page_repository import CompanyPageRepository
from app.repositories.company_repository import CompanyRepository
from app.utils.urls import normalize_url


def _data_to_dict(data: Any) -> dict[str, Any]:
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    return dict(data)


class CompanyPageService:
    def __init__(self, session: Session) -> None:
        self.company_repository = CompanyRepository(session)
        self.page_repository = CompanyPageRepository(session)

    def _require_company(self, company_id: str) -> None:
        if self.company_repository.get_by_id(company_id) is None:
            raise NotFoundError("Company not found")

    def create_or_update_page(self, company_id: str, data: Any) -> CompanyPage:
        self._require_company(company_id)
        values = _data_to_dict(data)
        values["company_id"] = company_id
        if url := values.get("url"):
            values["url"] = normalize_url(url)

        existing = self.page_repository.get_by_company_and_url(
            company_id, values["url"]
        )
        if existing is not None:
            return self.page_repository.update_page(existing, values)
        return self.page_repository.create_page(CompanyPage(**values))

    def get_page(self, page_id: str) -> CompanyPage:
        page = self.page_repository.get_by_id(page_id)
        if page is None:
            raise NotFoundError("Company page not found")
        return page

    def list_company_pages(
        self,
        company_id: str,
        offset: int = 0,
        limit: int = 50,
        page_type: str | None = None,
    ) -> list[CompanyPage]:
        self._require_company(company_id)
        return self.page_repository.list_by_company(
            company_id, offset=offset, limit=limit, page_type=page_type
        )

    def delete_page(self, page_id: str) -> None:
        self.page_repository.delete_page(self.get_page(page_id))

    def count_company_pages(
        self, company_id: str, page_type: str | None = None
    ) -> int:
        self._require_company(company_id)
        return self.page_repository.count_by_company(company_id, page_type=page_type)
