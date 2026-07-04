from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tech_stack_item import TechStackItem
from app.repositories.base import BaseRepository


class TechStackRepository(BaseRepository[TechStackItem]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, TechStackItem)

    def get_by_company_and_name(
        self, company_id: str, name: str, source: str | None = None
    ) -> TechStackItem | None:
        stmt = select(TechStackItem).where(
            TechStackItem.company_id == company_id,
            TechStackItem.name == name,
        )
        if source is not None:
            stmt = stmt.where(TechStackItem.source == source)
        return self.session.scalar(stmt)

    def list_by_company(self, company_id: str) -> list[TechStackItem]:
        stmt = select(TechStackItem).where(TechStackItem.company_id == company_id)
        return list(self.session.scalars(stmt).all())

    def create_item(self, item: TechStackItem) -> TechStackItem:
        return self.create(item)

    def update_item(self, item: TechStackItem, data: dict[str, Any]) -> TechStackItem:
        return self.update(item, data)

    def delete_item(self, item: TechStackItem) -> None:
        self.delete(item)
