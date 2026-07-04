from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model: type[T]) -> None:
        self.session = session
        self.model = model

    def get_by_id(self, id: str) -> T | None:
        return self.session.get(self.model, id)

    def list(self, offset: int = 0, limit: int = 50) -> list[T]:
        stmt = select(self.model).offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def create(self, obj: T) -> T:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def update(self, obj: T, data: dict[str, Any]) -> T:
        for key, value in data.items():
            setattr(obj, key, value)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        self.session.delete(obj)
        self.session.commit()

    def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return self.session.scalar(stmt) or 0
