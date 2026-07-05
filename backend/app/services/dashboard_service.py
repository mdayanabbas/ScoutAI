from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.crawl_run_repository import CrawlRunRepository
from app.repositories.job_repository import JobRepository
from app.schemas.dashboard import DashboardSummary, RecentActivityItem
from app.utils.enums import AgentRunStatus, CrawlStatus, JobStatus


RECENT_WINDOW_DAYS = 7


class DashboardService:
    def __init__(self, session: Session) -> None:
        self.company_repository = CompanyRepository(session)
        self.job_repository = JobRepository(session)
        self.crawl_run_repository = CrawlRunRepository(session)
        self.agent_run_repository = AgentRunRepository(session)

    def _today_start_utc(self) -> datetime:
        now = datetime.now(timezone.utc)
        return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    def _recent_since_utc(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=RECENT_WINDOW_DAYS)

    def get_summary(self) -> DashboardSummary:
        today_start = self._today_start_utc()
        recent_since = self._recent_since_utc()
        return DashboardSummary(
            total_companies=self.company_repository.count_companies(),
            total_jobs=self.job_repository.count_jobs(),
            active_jobs=self.job_repository.count_jobs(status=JobStatus.ACTIVE),
            remote_jobs=self.job_repository.count_remote_jobs(),
            companies_added_today=self.company_repository.count_created_since(
                today_start
            ),
            jobs_added_today=self.job_repository.count_created_since(today_start),
            recent_crawl_runs=self.crawl_run_repository.count_recent(
                since=recent_since
            ),
            successful_crawl_runs=self.crawl_run_repository.count_recent(
                status=CrawlStatus.SUCCESS, since=recent_since
            ),
            failed_crawl_runs=self.crawl_run_repository.count_recent(
                status=CrawlStatus.FAILED, since=recent_since
            ),
            recent_agent_runs=self.agent_run_repository.count_runs(since=recent_since),
            successful_agent_runs=self.agent_run_repository.count_runs(
                status=AgentRunStatus.SUCCESS, since=recent_since
            ),
            failed_agent_runs=self.agent_run_repository.count_runs(
                status=AgentRunStatus.FAILED, since=recent_since
            ),
        )

    def get_recent_activity(self, limit: int = 20) -> list[RecentActivityItem]:
        companies = [
            RecentActivityItem(
                type="company_created",
                title=f"Company added: {company.name}",
                description=company.normalized_domain,
                entity_id=company.id,
                created_at=company.created_at,
            )
            for company in self.company_repository.list_recent(limit=limit)
        ]
        jobs = [
            RecentActivityItem(
                type="job_created",
                title=f"Job added: {job.title}",
                description=job.normalized_title,
                entity_id=job.id,
                created_at=job.created_at,
            )
            for job in self.job_repository.list_recent(limit=limit)
        ]
        crawl_runs = [
            RecentActivityItem(
                type="crawl_run_created",
                title=f"Crawl run created: {crawl_run.status}",
                description=f"Company {crawl_run.company_id}",
                entity_id=crawl_run.id,
                created_at=crawl_run.created_at,
            )
            for crawl_run in self.crawl_run_repository.list_recent(limit=limit)
        ]
        agent_runs = [
            RecentActivityItem(
                type="agent_run_created",
                title=f"Agent run created: {agent_run.agent_name}",
                description=str(agent_run.status),
                entity_id=agent_run.id,
                created_at=agent_run.created_at,
            )
            for agent_run in self.agent_run_repository.list_recent(limit=limit)
        ]

        activity = companies + jobs + crawl_runs + agent_runs
        activity.sort(key=lambda item: item.created_at, reverse=True)
        return activity[:limit]
