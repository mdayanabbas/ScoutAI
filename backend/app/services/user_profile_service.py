from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.user_profile import UserProfile
from app.repositories.profile_repository import UserProfileRepository


def _data_to_dict(data: Any) -> dict[str, Any]:
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    return dict(data)


class UserProfileService:
    def __init__(self, session: Session) -> None:
        self.repository = UserProfileRepository(session)

    def get_profile(self) -> UserProfile | None:
        return self.repository.get_first_profile()

    def create_or_update_profile(self, data: Any) -> UserProfile:
        values = _data_to_dict(data)
        profile = self.repository.get_first_profile()
        if profile is None:
            return self.repository.create_profile(UserProfile(**values))
        return self.repository.update_profile(profile, values)

    def update_profile(self, data: Any) -> UserProfile:
        profile = self.repository.get_first_profile()
        if profile is None:
            raise NotFoundError("User profile not found")
        return self.repository.update_profile(profile, _data_to_dict(data))
