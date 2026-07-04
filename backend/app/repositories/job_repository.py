from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.repositories.base import BaseRepository
from app.utils.enums import JobStatus


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Job)

    def get_by_company_and_url(
        self, company_id: str, job_url: str
    ) -> Job | None:
        stmt = select(Job).where(
            Job.company_id == company_id, Job.job_url == job_url
        )
        return self.session.scalar(stmt)

    def _build_list_query(
        self,
        company_id: str | None = None,
        role_category: str | None = None,
        remote_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ):
        stmt = select(Job)
        if company_id is not None:
            stmt = stmt.where(Job.company_id == company_id)
        if role_category is not None:
            stmt = stmt.where(Job.role_category == role_category)
        if remote_type is not None:
            stmt = stmt.where(Job.remote_type == remote_type)
        if status is not None:
            stmt = stmt.where(Job.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(Job.title.ilike(pattern), Job.normalized_title.ilike(pattern))
            )
        return stmt

    def list_jobs(
        self,
        offset: int = 0,
        limit: int = 50,
        company_id: str | None = None,
        role_category: str | None = None,
        remote_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[Job]:
        stmt = self._build_list_query(
            company_id, role_category, remote_type, status, search
        )
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_active_jobs(
        self,
        company_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Job]:
        return self.list_jobs(
            offset=offset,
            limit=limit,
            company_id=company_id,
            status=JobStatus.ACTIVE.value,
        )

    def count_jobs(
        self,
        company_id: str | None = None,
        role_category: str | None = None,
        remote_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        stmt = self._build_list_query(
            company_id, role_category, remote_type, status, search
        )
        stmt = select(func.count()).select_from(stmt.subquery())
        return self.session.scalar(stmt) or 0

    def create_job(self, job: Job) -> Job:
        return self.create(job)

    def update_job(self, job: Job, data: dict[str, Any]) -> Job:
        return self.update(job, data)

    def delete_job(self, job: Job) -> None:
        self.delete(job)
