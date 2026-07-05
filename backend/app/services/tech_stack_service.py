from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.tech_stack_item import TechStackItem
from app.repositories.company_repository import CompanyRepository
from app.repositories.tech_stack_repository import TechStackRepository
from app.utils.text import normalize_text


def _data_to_dict(data: Any) -> dict[str, Any]:
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    return dict(data)


class TechStackService:
    def __init__(self, session: Session) -> None:
        self.company_repository = CompanyRepository(session)
        self.repository = TechStackRepository(session)

    def _require_company(self, company_id: str) -> None:
        if self.company_repository.get_by_id(company_id) is None:
            raise NotFoundError("Company not found")

    def create_or_update_item(self, company_id: str, data: Any) -> TechStackItem:
        self._require_company(company_id)
        values = _data_to_dict(data)
        values["company_id"] = company_id
        if name := values.get("name"):
            values["name"] = normalize_text(name)

        existing = self.repository.get_by_company_and_name(
            company_id, values["name"], source=values.get("source")
        )
        if existing is not None:
            return self.repository.update_item(existing, values)
        return self.repository.create_item(TechStackItem(**values))

    def list_company_tech_stack(self, company_id: str) -> list[TechStackItem]:
        self._require_company(company_id)
        return sorted(self.repository.list_by_company(company_id), key=lambda item: item.name)

    def update_item(self, item_id: str, data: Any) -> TechStackItem:
        item = self.repository.get_by_id(item_id)
        if item is None:
            raise NotFoundError("Tech stack item not found")

        values = _data_to_dict(data)
        if name := values.get("name"):
            values["name"] = normalize_text(name)

        lookup_name = values.get("name", item.name)
        lookup_source = values.get("source", item.source)
        existing = self.repository.get_by_company_and_name(
            item.company_id, lookup_name, source=lookup_source
        )
        if existing is not None and existing.id != item.id:
            raise ConflictError("Tech stack item already exists")

        return self.repository.update_item(item, values)

    def delete_item(self, item_id: str) -> None:
        item = self.repository.get_by_id(item_id)
        if item is None:
            raise NotFoundError("Tech stack item not found")
        self.repository.delete_item(item)
