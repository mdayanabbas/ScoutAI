from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Resume)

    def get_by_user_profile(self, resume_id: str, user_profile_id: str) -> Resume | None:
        stmt = select(Resume).where(
            Resume.id == resume_id,
            Resume.user_profile_id == user_profile_id,
        )
        return self.session.scalar(stmt)

    def get_active_for_user_profile(self, user_profile_id: str) -> Resume | None:
        stmt = (
            select(Resume)
            .where(Resume.user_profile_id == user_profile_id, Resume.is_active.is_(True))
            .order_by(Resume.updated_at.desc().nullslast(), Resume.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_for_user_profile(
        self, user_profile_id: str, *, limit: int = 50, offset: int = 0
    ) -> list[Resume]:
        stmt = (
            select(Resume)
            .where(Resume.user_profile_id == user_profile_id)
            .order_by(Resume.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def count_for_user_profile(self, user_profile_id: str) -> int:
        stmt = select(Resume).where(Resume.user_profile_id == user_profile_id)
        return len(list(self.session.scalars(stmt).all()))

    def set_active(self, resume: Resume) -> tuple[Resume, str | None]:
        previous = self.get_active_for_user_profile(resume.user_profile_id)
        previous_id = previous.id if previous and previous.id != resume.id else None
        self.session.execute(
            update(Resume)
            .where(Resume.user_profile_id == resume.user_profile_id)
            .values(is_active=False)
        )
        resume.is_active = True
        self.session.add(resume)
        self.session.commit()
        self.session.refresh(resume)
        return resume, previous_id
