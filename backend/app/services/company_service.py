from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository
from app.utils.urls import normalize_domain, normalize_url


def _data_to_dict(data: Any) -> dict[str, Any]:
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    return dict(data)


class CompanyService:
    def __init__(self, session: Session) -> None:
        self.repository = CompanyRepository(session)

    def create_company(self, data: Any) -> Company:
        values = _data_to_dict(data)
        if website_url := values.get("website_url"):
            values["website_url"] = normalize_url(website_url)
            values["normalized_domain"] = normalize_domain(website_url)
        elif domain := values.get("normalized_domain"):
            values["normalized_domain"] = normalize_domain(domain)

        normalized_domain = values.get("normalized_domain")
        if normalized_domain and self.repository.get_by_domain(normalized_domain):
            raise ConflictError("Company already exists")

        return self.repository.create_company(Company(**values))

    def get_company(self, company_id: str) -> Company:
        company = self.repository.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company

    def get_company_by_domain(self, domain: str) -> Company:
        company = self.repository.get_by_domain(normalize_domain(domain))
        if company is None:
            raise NotFoundError("Company not found")
        return company

    def list_companies(
        self,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        source: str | None = None,
        stage: str | None = None,
        is_active: bool | None = None,
    ) -> list[Company]:
        return self.repository.list_companies(
            offset=offset,
            limit=limit,
            search=search,
            source=source,
            stage=stage,
            is_active=is_active,
        )

    def update_company(self, company_id: str, data: Any) -> Company:
        company = self.get_company(company_id)
        values = _data_to_dict(data)
        if website_url := values.get("website_url"):
            values["website_url"] = normalize_url(website_url)
            values["normalized_domain"] = normalize_domain(website_url)
        elif domain := values.get("normalized_domain"):
            values["normalized_domain"] = normalize_domain(domain)

        normalized_domain = values.get("normalized_domain")
        existing = (
            self.repository.get_by_domain(normalized_domain)
            if normalized_domain
            else None
        )
        if existing is not None and existing.id != company.id:
            raise ConflictError("Company already exists")

        return self.repository.update_company(company, values)

    def delete_company(self, company_id: str) -> None:
        self.repository.delete_company(self.get_company(company_id))

    def count_companies(
        self,
        search: str | None = None,
        source: str | None = None,
        stage: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        return self.repository.count_companies(
            search=search, source=source, stage=stage, is_active=is_active
        )
