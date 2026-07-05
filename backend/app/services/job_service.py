from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.job import Job
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.utils.text import normalize_title
from app.utils.urls import normalize_url


def _data_to_dict(data: Any) -> dict[str, Any]:
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    return dict(data)


class JobService:
    def __init__(self, session: Session) -> None:
        self.company_repository = CompanyRepository(session)
        self.job_repository = JobRepository(session)

    def _require_company(self, company_id: str) -> None:
        if self.company_repository.get_by_id(company_id) is None:
            raise NotFoundError("Company not found")

    def create_or_update_job(self, company_id: str, data: Any) -> Job:
        self._require_company(company_id)
        values = _data_to_dict(data)
        values["company_id"] = company_id
        if title := values.get("title"):
            values["normalized_title"] = normalize_title(title)
        if job_url := values.get("job_url"):
            values["job_url"] = normalize_url(job_url)

        existing = None
        if values.get("job_url"):
            existing = self.job_repository.get_by_company_and_url(
                company_id, values["job_url"]
            )

        if existing is not None:
            values["last_seen_at"] = datetime.now(timezone.utc)
            return self.job_repository.update_job(existing, values)
        return self.job_repository.create_job(Job(**values))

    def get_job(self, job_id: str) -> Job:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        return job

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
        return self.job_repository.list_jobs(
            offset=offset,
            limit=limit,
            company_id=company_id,
            role_category=role_category,
            remote_type=remote_type,
            status=status,
            search=search,
        )

    def list_company_jobs(
        self,
        company_id: str,
        offset: int = 0,
        limit: int = 50,
        role_category: str | None = None,
        remote_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[Job]:
        self._require_company(company_id)
        return self.list_jobs(
            offset=offset,
            limit=limit,
            company_id=company_id,
            role_category=role_category,
            remote_type=remote_type,
            status=status,
            search=search,
        )

    def list_active_jobs(
        self, company_id: str | None = None, offset: int = 0, limit: int = 50
    ) -> list[Job]:
        return self.job_repository.list_active_jobs(
            company_id=company_id, offset=offset, limit=limit
        )

    def update_job(self, job_id: str, data: Any) -> Job:
        job = self.get_job(job_id)
        values = _data_to_dict(data)
        if title := values.get("title"):
            values["normalized_title"] = normalize_title(title)
        if job_url := values.get("job_url"):
            values["job_url"] = normalize_url(job_url)
            existing = self.job_repository.get_by_company_and_url(
                job.company_id, values["job_url"]
            )
            if existing is not None and existing.id != job.id:
                raise ConflictError("Job already exists")
        return self.job_repository.update_job(job, values)

    def delete_job(self, job_id: str) -> None:
        self.job_repository.delete_job(self.get_job(job_id))

    def count_jobs(
        self,
        company_id: str | None = None,
        role_category: str | None = None,
        remote_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        return self.job_repository.count_jobs(
            company_id=company_id,
            role_category=role_category,
            remote_type=remote_type,
            status=status,
            search=search,
        )

    def count_company_jobs(
        self,
        company_id: str,
        role_category: str | None = None,
        remote_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        self._require_company(company_id)
        return self.count_jobs(
            company_id=company_id,
            role_category=role_category,
            remote_type=remote_type,
            status=status,
            search=search,
        )
