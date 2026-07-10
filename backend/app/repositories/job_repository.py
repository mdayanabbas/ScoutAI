from datetime import datetime, timezone
from typing import Any

from sqlalchemy import case, func, nullsfirst, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.job import Job
from app.repositories.base import BaseRepository
from app.utils.enums import JobEnrichmentStatus, JobStatus, RemoteType

ENRICHMENT_UPDATE_FIELDS = {
    "seniority",
    "employment_type",
    "apply_url",
    "published_at",
    "last_verified_at",
    "salary_text",
    "equity_mentioned",
    "visa_sponsorship",
    "work_authorization",
    "required_skills_json",
    "preferred_skills_json",
    "technologies_json",
    "enrichment_status",
    "enrichment_confidence",
    "enriched_at",
}


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Job)

    def get_by_company_and_url(
        self, company_id: str, job_url: str
    ) -> Job | None:
        stmt = (
            select(Job)
            .options(selectinload(Job.company))
            .where(Job.company_id == company_id, Job.job_url == job_url)
        )
        return self.session.scalar(stmt)

    def get_by_id(self, id: str) -> Job | None:
        stmt = select(Job).options(selectinload(Job.company)).where(Job.id == id)
        return self.session.scalar(stmt)

    def get_by_discovery_candidate_id(self, candidate_id: str) -> Job | None:
        stmt = select(Job).where(Job.discovery_candidate_id == candidate_id)
        return self.session.scalar(stmt)

    def get_legacy_match(
        self,
        company_id: str,
        job_url: str,
        normalized_title: str,
    ) -> Job | None:
        stmt = select(Job).where(
            Job.company_id == company_id,
            Job.job_url == job_url,
            Job.normalized_title == normalized_title,
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
        stmt = (
            stmt.options(selectinload(Job.company))
            .order_by(Job.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
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

    def count_created_since(self, since: datetime) -> int:
        stmt = select(func.count()).select_from(Job).where(Job.created_at >= since)
        return self.session.scalar(stmt) or 0

    def count_remote_jobs(self) -> int:
        remote_types = (
            RemoteType.REMOTE_COUNTRY,
            RemoteType.REMOTE_REGION,
            RemoteType.REMOTE_WORLDWIDE,
        )
        stmt = select(func.count()).select_from(Job).where(
            Job.remote_type.in_(remote_types)
        )
        return self.session.scalar(stmt) or 0

    def list_recent(self, limit: int = 20) -> list[Job]:
        stmt = (
            select(Job)
            .options(selectinload(Job.company))
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_jobs_needing_enrichment(
        self, limit: int = 50, offset: int = 0
    ) -> list[Job]:
        stmt = (
            select(Job)
            .where(
                Job.enrichment_status.in_(
                    {"not_enriched", "partially_enriched", "unresolved"}
                )
                | Job.last_verified_at.is_(None)
            )
            .where(Job.enrichment_status != "failed")
            .order_by(
                case((Job.enrichment_status == "not_enriched", 0), else_=1),
                nullsfirst(Job.last_verified_at.asc()),
                Job.created_at.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def mark_enrichment_pending(self, job_id: str) -> Job:
        job = self.get_by_id(job_id)
        if job is None:
            raise ValueError("Job not found")
        return self.update_job(job, {"enrichment_status": "pending"})

    def update_enrichment_fields(self, job_id: str, fields: dict[str, Any]) -> Job:
        unknown = set(fields) - ENRICHMENT_UPDATE_FIELDS
        if unknown:
            raise ValueError(f"Unsupported enrichment fields: {', '.join(sorted(unknown))}")
        job = self.get_by_id(job_id)
        if job is None:
            raise ValueError("Job not found")
        values = dict(fields)
        status = values.get("enrichment_status")
        checked_statuses = {
            JobEnrichmentStatus.ENRICHED.value,
            JobEnrichmentStatus.PARTIALLY_ENRICHED.value,
            JobEnrichmentStatus.UNRESOLVED.value,
        }
        if status == JobEnrichmentStatus.ENRICHED.value and "enriched_at" not in values:
            values["enriched_at"] = datetime.now(timezone.utc)
        if status in checked_statuses and "last_verified_at" not in values:
            values["last_verified_at"] = datetime.now(timezone.utc)
        return self.update_job(job, values)

    def mark_enrichment_failed(self, job_id: str) -> Job:
        job = self.get_by_id(job_id)
        if job is None:
            raise ValueError("Job not found")
        return self.update_job(job, {"enrichment_status": "failed"})

    def mark_enrichment_unresolved(self, job_id: str) -> Job:
        job = self.get_by_id(job_id)
        if job is None:
            raise ValueError("Job not found")
        return self.update_job(job, {"enrichment_status": "unresolved"})

    def create_job(self, job: Job) -> Job:
        return self.create(job)

    def update_job(self, job: Job, data: dict[str, Any]) -> Job:
        return self.update(job, data)

    def delete_job(self, job: Job) -> None:
        self.delete(job)
