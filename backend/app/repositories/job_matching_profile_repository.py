from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job_matching_profile import JobMatchingProfile
from app.repositories.base import BaseRepository


class JobMatchingProfileRepository(BaseRepository[JobMatchingProfile]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, JobMatchingProfile)

    def get_by_user_profile_id(self, user_profile_id: str) -> JobMatchingProfile | None:
        stmt = select(JobMatchingProfile).where(
            JobMatchingProfile.user_profile_id == user_profile_id
        )
        return self.session.scalar(stmt)

    def create_profile(self, profile: JobMatchingProfile) -> JobMatchingProfile:
        return self.create(profile)

    def update_profile(
        self, profile: JobMatchingProfile, data: dict[str, Any]
    ) -> JobMatchingProfile:
        return self.update(profile, data)

    def create_or_update(
        self, user_profile_id: str, data: dict[str, Any]
    ) -> JobMatchingProfile:
        existing = self.get_by_user_profile_id(user_profile_id)
        if existing is not None:
            return self.update_profile(existing, data)
        try:
            return self.create_profile(
                JobMatchingProfile(user_profile_id=user_profile_id, **data)
            )
        except IntegrityError:
            self.session.rollback()
            existing = self.get_by_user_profile_id(user_profile_id)
            if existing is None:
                raise
            return self.update_profile(existing, data)

    def exists_for_user_profile(self, user_profile_id: str) -> bool:
        return self.get_by_user_profile_id(user_profile_id) is not None

    def delete_profile(self, profile: JobMatchingProfile) -> None:
        self.delete(profile)

