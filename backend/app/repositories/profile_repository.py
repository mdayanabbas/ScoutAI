from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.repositories.base import BaseRepository


class UserProfileRepository(BaseRepository[UserProfile]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, UserProfile)

    def get_first_profile(self) -> UserProfile | None:
        stmt = select(UserProfile).limit(1)
        return self.session.scalar(stmt)

    def create_profile(self, profile: UserProfile) -> UserProfile:
        return self.create(profile)

    def update_profile(
        self, profile: UserProfile, data: dict[str, Any]
    ) -> UserProfile:
        return self.update(profile, data)
