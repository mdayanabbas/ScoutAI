from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.company import Company
from app.models.company_watchlist import CompanyWatchlistItem
from app.models.job import Job
from app.models.job_match import JobMatch
from app.repositories.base import BaseRepository

ACTIVE_WATCH_STATUSES = {"watching", "interested", "contacted", "applied", "paused"}


class CompanyWatchlistRepository(BaseRepository[CompanyWatchlistItem]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CompanyWatchlistItem)

    def get_by_id(self, id: str) -> CompanyWatchlistItem | None:
        stmt = (
            select(CompanyWatchlistItem)
            .options(selectinload(CompanyWatchlistItem.company))
            .where(CompanyWatchlistItem.id == id)
        )
        return self.session.scalar(stmt)

    def list_items(
        self,
        *,
        watch_status: str | None = None,
        priority: str | None = None,
        remote_interest: str | None = None,
        junior_friendliness_signal: str | None = None,
        tag: str | None = None,
        search: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CompanyWatchlistItem]:
        stmt = self._filtered_query(
            watch_status=watch_status,
            priority=priority,
            remote_interest=remote_interest,
            junior_friendliness_signal=junior_friendliness_signal,
            tag=tag,
            search=search,
            include_archived=include_archived,
        )
        priority_order = case(
            (CompanyWatchlistItem.priority == "high", 0),
            (CompanyWatchlistItem.priority == "medium", 1),
            else_=2,
        )
        stmt = (
            stmt.options(selectinload(CompanyWatchlistItem.company))
            .order_by(priority_order, CompanyWatchlistItem.updated_at.desc().nullslast(), CompanyWatchlistItem.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def count_items(
        self,
        *,
        watch_status: str | None = None,
        priority: str | None = None,
        remote_interest: str | None = None,
        junior_friendliness_signal: str | None = None,
        tag: str | None = None,
        search: str | None = None,
        include_archived: bool = False,
    ) -> int:
        stmt = self._filtered_query(
            watch_status=watch_status,
            priority=priority,
            remote_interest=remote_interest,
            junior_friendliness_signal=junior_friendliness_signal,
            tag=tag,
            search=search,
            include_archived=include_archived,
        )
        return self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    def archive(self, item: CompanyWatchlistItem) -> CompanyWatchlistItem:
        return self.update(item, {"watch_status": "archived"})

    def find_active_duplicate(
        self,
        *,
        company_id: str | None,
        normalized_company_name: str,
        normalized_domain: str | None,
    ) -> CompanyWatchlistItem | None:
        stmt = select(CompanyWatchlistItem).where(CompanyWatchlistItem.watch_status != "archived")
        if company_id:
            stmt = stmt.where(CompanyWatchlistItem.company_id == company_id)
        else:
            stmt = stmt.where(CompanyWatchlistItem.normalized_company_name == normalized_company_name)
            if normalized_domain:
                stmt = stmt.where(CompanyWatchlistItem.normalized_domain == normalized_domain)
        return self.session.scalar(stmt.order_by(CompanyWatchlistItem.updated_at.desc().nullslast()).limit(1))

    def find_archived_duplicate(
        self,
        *,
        company_id: str | None,
        normalized_company_name: str,
        normalized_domain: str | None,
    ) -> CompanyWatchlistItem | None:
        stmt = select(CompanyWatchlistItem).where(CompanyWatchlistItem.watch_status == "archived")
        if company_id:
            stmt = stmt.where(CompanyWatchlistItem.company_id == company_id)
        else:
            stmt = stmt.where(CompanyWatchlistItem.normalized_company_name == normalized_company_name)
            if normalized_domain:
                stmt = stmt.where(CompanyWatchlistItem.normalized_domain == normalized_domain)
        return self.session.scalar(stmt.order_by(CompanyWatchlistItem.updated_at.desc().nullslast()).limit(1))

    def get_by_company_id(self, company_id: str) -> list[CompanyWatchlistItem]:
        stmt = select(CompanyWatchlistItem).where(CompanyWatchlistItem.company_id == company_id)
        return list(self.session.scalars(stmt).all())

    def get_stats(self) -> dict[str, int]:
        status_counts = dict(
            self.session.execute(
                select(CompanyWatchlistItem.watch_status, func.count()).group_by(CompanyWatchlistItem.watch_status)
            ).all()
        )
        priority_counts = dict(
            self.session.execute(
                select(CompanyWatchlistItem.priority, func.count()).group_by(CompanyWatchlistItem.priority)
            ).all()
        )
        items = list(self.session.scalars(select(CompanyWatchlistItem)).all())
        recent_since = datetime.now(timezone.utc) - timedelta(days=30)
        review_since = datetime.now(timezone.utc) - timedelta(days=14)
        with_recommended = 0
        with_recent = 0
        needs_review = 0
        for item in items:
            recommended = self.count_recommended_jobs_for_company(item) > 0
            recent = self.count_jobs_for_company(item, published_since=recent_since) > 0
            if recommended:
                with_recommended += 1
            if recent:
                with_recent += 1
            if item.priority == "high" and (item.last_reviewed_at is None or item.last_reviewed_at < review_since):
                needs_review += 1
            elif recent and recommended:
                needs_review += 1
        return {
            "total": len(items),
            "watching": status_counts.get("watching", 0),
            "interested": status_counts.get("interested", 0),
            "contacted": status_counts.get("contacted", 0),
            "applied": status_counts.get("applied", 0),
            "paused": status_counts.get("paused", 0),
            "archived": status_counts.get("archived", 0),
            "high_priority": priority_counts.get("high", 0),
            "medium_priority": priority_counts.get("medium", 0),
            "low_priority": priority_counts.get("low", 0),
            "with_recommended_jobs": with_recommended,
            "with_recent_jobs": with_recent,
            "needs_review": needs_review,
        }

    def count_jobs_for_company(
        self,
        item: CompanyWatchlistItem,
        *,
        active_only: bool = False,
        published_since: datetime | None = None,
    ) -> int:
        stmt = self._jobs_query_for_item(item)
        if active_only:
            stmt = stmt.where(Job.status == "active")
        if published_since is not None:
            stmt = stmt.where(Job.published_at >= published_since)
        return self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    def count_recommended_jobs_for_company(self, item: CompanyWatchlistItem) -> int:
        stmt = self._jobs_query_for_item(item).join(JobMatch, JobMatch.job_id == Job.id)
        stmt = stmt.where(JobMatch.eligibility_status != "unsuitable")
        subquery = stmt.with_only_columns(Job.id).subquery()
        return self.session.scalar(select(func.count(func.distinct(subquery.c.id)))) or 0

    def get_latest_job_for_company(self, item: CompanyWatchlistItem) -> Job | None:
        stmt = self._jobs_query_for_item(item).order_by(Job.published_at.desc().nullslast(), Job.created_at.desc()).limit(1)
        return self.session.scalar(stmt)

    def list_jobs_for_watchlist_item(
        self,
        item: CompanyWatchlistItem,
        *,
        recommended_only: bool = False,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[Job, JobMatch | None]]:
        stmt = (
            self._jobs_query_for_item(item)
            .options(selectinload(Job.company))
            .outerjoin(JobMatch, JobMatch.job_id == Job.id)
            .add_columns(JobMatch)
        )
        if recommended_only:
            stmt = stmt.where(JobMatch.eligibility_status != "unsuitable")
        if active_only:
            stmt = stmt.where(Job.status == "active")
        stmt = stmt.order_by(Job.published_at.desc().nullslast(), Job.created_at.desc()).offset(offset).limit(limit)
        return list(self.session.execute(stmt).all())

    def count_list_jobs_for_watchlist_item(
        self,
        item: CompanyWatchlistItem,
        *,
        recommended_only: bool = False,
        active_only: bool = False,
    ) -> int:
        stmt = self._jobs_query_for_item(item)
        if recommended_only:
            stmt = stmt.join(JobMatch, JobMatch.job_id == Job.id).where(JobMatch.eligibility_status != "unsuitable")
        if active_only:
            stmt = stmt.where(Job.status == "active")
        return self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    def _filtered_query(
        self,
        *,
        watch_status: str | None,
        priority: str | None,
        remote_interest: str | None,
        junior_friendliness_signal: str | None,
        tag: str | None,
        search: str | None,
        include_archived: bool,
    ):
        stmt = select(CompanyWatchlistItem)
        if watch_status:
            stmt = stmt.where(CompanyWatchlistItem.watch_status == watch_status)
        elif not include_archived:
            stmt = stmt.where(CompanyWatchlistItem.watch_status != "archived")
        if priority:
            stmt = stmt.where(CompanyWatchlistItem.priority == priority)
        if remote_interest:
            stmt = stmt.where(CompanyWatchlistItem.remote_interest == remote_interest)
        if junior_friendliness_signal:
            stmt = stmt.where(CompanyWatchlistItem.junior_friendliness_signal == junior_friendliness_signal)
        if tag:
            stmt = stmt.where(CompanyWatchlistItem.tags_json.contains([tag]))
        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(CompanyWatchlistItem.company_name).like(pattern),
                    CompanyWatchlistItem.normalized_company_name.like(pattern),
                    CompanyWatchlistItem.normalized_domain.like(pattern),
                )
            )
        return stmt

    def _jobs_query_for_item(self, item: CompanyWatchlistItem):
        stmt = select(Job)
        if item.company_id:
            return stmt.where(Job.company_id == item.company_id)
        conditions = []
        if item.normalized_company_name:
            conditions.append(
                Job.company_id.in_(
                    select(Company.id).where(func.lower(Company.name) == item.normalized_company_name)
                )
            )
        if item.normalized_domain:
            conditions.append(
                Job.company_id.in_(
                    select(Company.id).where(Company.normalized_domain == item.normalized_domain)
                )
            )
        if not conditions:
            return stmt.where(False)
        return stmt.where(or_(*conditions))
