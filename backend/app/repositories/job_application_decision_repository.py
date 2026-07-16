from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.job_application_decision import JobApplicationDecision
from app.repositories.base import BaseRepository


class JobApplicationDecisionRepository(BaseRepository[JobApplicationDecision]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, JobApplicationDecision)

    def get_by_job_and_user_profile(self, job_id: str, user_profile_id: str) -> JobApplicationDecision | None:
        stmt = (
            select(JobApplicationDecision)
            .options(selectinload(JobApplicationDecision.job))
            .where(
                JobApplicationDecision.job_id == job_id,
                JobApplicationDecision.user_profile_id == user_profile_id,
            )
        )
        return self.session.scalar(stmt)

    def list_for_user_profile(
        self,
        user_profile_id: str,
        *,
        status: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JobApplicationDecision]:
        stmt = (
            select(JobApplicationDecision)
            .options(selectinload(JobApplicationDecision.job))
            .where(JobApplicationDecision.user_profile_id == user_profile_id)
        )
        if status:
            stmt = stmt.where(JobApplicationDecision.status == status)
        elif not include_archived:
            stmt = stmt.where(JobApplicationDecision.status != "archived")
        stmt = stmt.order_by(JobApplicationDecision.updated_at.desc().nullslast(), JobApplicationDecision.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def count_for_user_profile(
        self,
        user_profile_id: str,
        *,
        status: str | None = None,
        include_archived: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(JobApplicationDecision).where(
            JobApplicationDecision.user_profile_id == user_profile_id
        )
        if status:
            stmt = stmt.where(JobApplicationDecision.status == status)
        elif not include_archived:
            stmt = stmt.where(JobApplicationDecision.status != "archived")
        return self.session.scalar(stmt) or 0

    def status_counts(self, user_profile_id: str) -> dict[str, int]:
        stmt = (
            select(JobApplicationDecision.status, func.count())
            .where(JobApplicationDecision.user_profile_id == user_profile_id)
            .group_by(JobApplicationDecision.status)
        )
        return {status: count for status, count in self.session.execute(stmt).all()}
