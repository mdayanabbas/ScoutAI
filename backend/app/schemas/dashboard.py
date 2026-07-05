from datetime import datetime

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: int = 0


class RecentActivityItem(BaseModel):
    type: str
    title: str
    description: str | None = None
    entity_id: str
    created_at: datetime


class DashboardSummary(BaseModel):
    total_companies: int = 0
    total_jobs: int = 0
    active_jobs: int = 0
    remote_jobs: int = 0
    companies_added_today: int = 0
    jobs_added_today: int = 0
    recent_crawl_runs: int = 0
    successful_crawl_runs: int = 0
    failed_crawl_runs: int = 0
    recent_agent_runs: int = 0
    successful_agent_runs: int = 0
    failed_agent_runs: int = 0


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    recent_activity: list[RecentActivityItem]
