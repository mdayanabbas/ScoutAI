from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.company import Company
from app.models.company_watchlist import CompanyWatchlistItem
from app.models.job import Job
from app.models.job_match import JobMatch
from app.repositories.company_repository import CompanyRepository
from app.repositories.company_watchlist_repository import CompanyWatchlistRepository
from app.repositories.job_repository import JobRepository
from app.schemas.company_watchlist import (
    CompanyWatchlistCreate,
    CompanyWatchlistJobRead,
    CompanyWatchlistJobsResponse,
    CompanyWatchlistListResponse,
    CompanyWatchlistResponse,
    CompanyWatchlistStatsResponse,
    CompanyWatchlistUpdate,
)

logger = logging.getLogger(__name__)


class CompanyWatchlistService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = CompanyWatchlistRepository(session)
        self.company_repository = CompanyRepository(session)
        self.job_repository = JobRepository(session)

    def create_watchlist_item(self, payload: CompanyWatchlistCreate) -> CompanyWatchlistResponse:
        values, company = self._create_values(payload)
        duplicate = self.repository.find_active_duplicate(
            company_id=values["company_id"],
            normalized_company_name=values["normalized_company_name"],
            normalized_domain=values["normalized_domain"],
        )
        if duplicate is not None:
            logger.info("Duplicate company watchlist item detected", extra={"watchlist_item_id": duplicate.id})
            raise ConflictError("Company is already on the active watchlist")

        archived = self.repository.find_archived_duplicate(
            company_id=values["company_id"],
            normalized_company_name=values["normalized_company_name"],
            normalized_domain=values["normalized_domain"],
        )
        if archived is not None:
            item = self.repository.update(archived, values)
            logger.info("Company watchlist item updated", extra={"watchlist_item_id": item.id})
            return self._response(item)

        item = self.repository.create(CompanyWatchlistItem(**values))
        logger.info("Company watchlist item created", extra={"watchlist_item_id": item.id, "company_id": getattr(company, "id", None)})
        return self._response(item)

    def list_watchlist_items(
        self,
        *,
        watch_status: str | None = None,
        priority: str | None = None,
        remote_interest: str | None = None,
        junior_friendliness_signal: str | None = None,
        tag: str | None = None,
        search: str | None = None,
        has_recommended_jobs: bool | None = None,
        has_recent_jobs: bool | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> CompanyWatchlistListResponse:
        items = self.repository.list_items(
            watch_status=watch_status,
            priority=priority,
            remote_interest=remote_interest,
            junior_friendliness_signal=junior_friendliness_signal,
            tag=tag,
            search=search,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )
        if has_recommended_jobs is not None:
            items = [item for item in items if (self.repository.count_recommended_jobs_for_company(item) > 0) is has_recommended_jobs]
        if has_recent_jobs is not None:
            recent_since = datetime.now(timezone.utc) - timedelta(days=30)
            items = [
                item
                for item in items
                if (self.repository.count_jobs_for_company(item, published_since=recent_since) > 0) is has_recent_jobs
            ]
        total = self.repository.count_items(
            watch_status=watch_status,
            priority=priority,
            remote_interest=remote_interest,
            junior_friendliness_signal=junior_friendliness_signal,
            tag=tag,
            search=search,
            include_archived=include_archived,
        )
        return CompanyWatchlistListResponse(
            items=[self._response(item) for item in items],
            total=total if has_recommended_jobs is None and has_recent_jobs is None else len(items),
            limit=limit,
            offset=offset,
        )

    def get_watchlist_item(self, item_id: str) -> CompanyWatchlistResponse:
        return self._response(self._get_item(item_id))

    def update_watchlist_item(self, item_id: str, payload: CompanyWatchlistUpdate) -> CompanyWatchlistResponse:
        item = self._get_item(item_id)
        values = payload.model_dump(exclude_unset=True)
        values = self._map_update_values(values, item)
        updated = self.repository.update(item, values)
        logger.info("Company watchlist item updated", extra={"watchlist_item_id": updated.id})
        return self._response(updated)

    def archive_watchlist_item(self, item_id: str) -> CompanyWatchlistResponse:
        item = self.repository.archive(self._get_item(item_id))
        logger.info("Company watchlist item archived", extra={"watchlist_item_id": item.id})
        return self._response(item)

    def delete_watchlist_item(self, item_id: str) -> None:
        item = self._get_item(item_id)
        self.repository.delete(item)
        logger.info("Company watchlist item deleted", extra={"watchlist_item_id": item_id})

    def get_stats(self) -> CompanyWatchlistStatsResponse:
        return CompanyWatchlistStatsResponse(**self.repository.get_stats())

    def list_jobs_for_item(
        self,
        item_id: str,
        *,
        recommended_only: bool = False,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> CompanyWatchlistJobsResponse:
        item = self._get_item(item_id)
        rows = self.repository.list_jobs_for_watchlist_item(
            item,
            recommended_only=recommended_only,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )
        total = self.repository.count_list_jobs_for_watchlist_item(
            item,
            recommended_only=recommended_only,
            active_only=active_only,
        )
        return CompanyWatchlistJobsResponse(
            watchlist_item=self._response(item),
            jobs=[self._job_response(job, match) for job, match in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def watch_company_from_job(
        self,
        job_id: str,
        payload: CompanyWatchlistCreate | None = None,
    ) -> CompanyWatchlistResponse:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        data = payload or CompanyWatchlistCreate(company_id=job.company_id)
        target_roles = list(data.target_roles)
        role = _stringify(job.role_category) or job.title
        if role and role not in target_roles:
            target_roles.append(role)
        create_payload = data.model_copy(
            update={
                "company_id": job.company_id,
                "company_name": data.company_name or getattr(job.company, "name", None),
                "target_roles": target_roles,
            }
        )
        try:
            response = self.create_watchlist_item(create_payload)
            item = self.repository.get_by_id(response.id)
            if item is not None:
                response = self._response(
                    self.repository.update(item, {"last_job_seen_at": job.published_at or job.created_at})
                )
        except ConflictError:
            item = self.repository.find_active_duplicate(
                company_id=job.company_id,
                normalized_company_name=normalize_company_name(getattr(job.company, "name", "")),
                normalized_domain=normalize_domain(getattr(job.company, "normalized_domain", None)),
            )
            if item is None:
                raise
            response = self._response(
                self.repository.update(
                    item,
                    {
                        "last_job_seen_at": job.published_at or job.created_at,
                        "target_roles_json": sorted(set((item.target_roles_json or []) + target_roles)),
                    },
                )
            )
        logger.info("Company watchlist item created from job", extra={"job_id": job_id, "watchlist_item_id": response.id})
        return response

    def _get_item(self, item_id: str) -> CompanyWatchlistItem:
        item = self.repository.get_by_id(item_id)
        if item is None:
            raise NotFoundError("Company watchlist item not found")
        return item

    def _create_values(self, payload: CompanyWatchlistCreate) -> tuple[dict, Company | None]:
        company = self._resolve_company(payload.company_id, payload.company_name, payload.company_domain)
        if payload.company_id and company is None:
            raise NotFoundError("Company not found")
        company_name = payload.company_name or getattr(company, "name", None)
        if not company_name:
            raise NotFoundError("Company not found")
        company_domain = payload.company_domain or getattr(company, "normalized_domain", None)
        company_url = payload.company_url or getattr(company, "website_url", None)
        normalized_domain = normalize_domain(company_domain or company_url)
        return (
            {
                "company_id": getattr(company, "id", None),
                "company_name": company_name,
                "company_domain": company_domain,
                "company_url": company_url,
                "normalized_company_name": normalize_company_name(company_name),
                "normalized_domain": normalized_domain,
                "watch_status": payload.watch_status,
                "priority": payload.priority,
                "interest_reason": payload.interest_reason,
                "target_roles_json": payload.target_roles,
                "preferred_locations_json": payload.preferred_locations,
                "notes": payload.notes,
                "tags_json": payload.tags,
                "remote_interest": payload.remote_interest,
                "junior_friendliness_signal": payload.junior_friendliness_signal,
            },
            company,
        )

    def _resolve_company(
        self,
        company_id: str | None,
        company_name: str | None,
        company_domain: str | None,
    ) -> Company | None:
        if company_id:
            return self.company_repository.get_by_id(company_id)
        normalized_domain = normalize_domain(company_domain)
        if normalized_domain:
            company = self.company_repository.get_by_domain(normalized_domain)
            if company is not None:
                return company
        normalized_name = normalize_company_name(company_name or "")
        if normalized_name:
            return self.session.query(Company).filter(Company.name.ilike(company_name or "")).first()
        return None

    def _map_update_values(self, values: dict, item: CompanyWatchlistItem) -> dict:
        mapped: dict = {}
        for key, value in values.items():
            if key == "target_roles":
                mapped["target_roles_json"] = value
            elif key == "preferred_locations":
                mapped["preferred_locations_json"] = value
            elif key == "tags":
                mapped["tags_json"] = value
            else:
                mapped[key] = value
        company_name = mapped.get("company_name", item.company_name)
        company_domain = mapped.get("company_domain", item.company_domain)
        company_url = mapped.get("company_url", item.company_url)
        if "company_name" in mapped:
            mapped["normalized_company_name"] = normalize_company_name(company_name)
        if "company_domain" in mapped or "company_url" in mapped:
            mapped["normalized_domain"] = normalize_domain(company_domain or company_url)
        return mapped

    def _response(self, item: CompanyWatchlistItem) -> CompanyWatchlistResponse:
        latest = self.repository.get_latest_job_for_company(item)
        return CompanyWatchlistResponse(
            id=item.id,
            company_id=item.company_id,
            company_name=item.company_name,
            company_domain=item.company_domain,
            company_url=item.company_url,
            watch_status=item.watch_status,
            priority=item.priority,
            interest_reason=item.interest_reason,
            target_roles=item.target_roles_json or [],
            preferred_locations=item.preferred_locations_json or [],
            notes=item.notes,
            tags=item.tags_json or [],
            remote_interest=item.remote_interest,
            junior_friendliness_signal=item.junior_friendliness_signal,
            last_reviewed_at=item.last_reviewed_at,
            last_job_seen_at=item.last_job_seen_at,
            job_count=self.repository.count_jobs_for_company(item),
            recommended_job_count=self.repository.count_recommended_jobs_for_company(item),
            latest_job_title=getattr(latest, "title", None),
            latest_job_published_at=getattr(latest, "published_at", None),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _job_response(self, job: Job, match: JobMatch | None) -> CompanyWatchlistJobRead:
        return CompanyWatchlistJobRead(
            id=job.id,
            company_id=job.company_id,
            company_name=getattr(job.company, "name", None),
            title=job.title,
            normalized_title=job.normalized_title,
            role_category=_stringify(job.role_category),
            location=job.location,
            remote_type=_stringify(job.remote_type),
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            job_url=job.job_url,
            apply_url=job.apply_url,
            source_platform=job.source_platform,
            status=_stringify(job.status),
            published_at=job.published_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
            match_tier=getattr(match, "match_tier", None),
            total_score=getattr(match, "total_score", None),
            eligibility_status=getattr(match, "eligibility_status", None),
        )


def normalize_company_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().lower()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = parsed.netloc or parsed.path.split("/")[0]
    host = host.removeprefix("www.")
    return host or None


def _stringify(value) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", str(value))
