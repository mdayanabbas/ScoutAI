from datetime import datetime

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: int = 0


class RecentActivityItem(BaseModel):
    id: str
    label: str
    activity_type: str
    created_at: datetime


class DashboardSummary(BaseModel):
    new_startups_today: int = 0
    funded_recently: int = 0
    hiring_now: int = 0
    remote_friendly: int = 0
    strong_matches: int = 0
    founder_hiring_signals: int = 0
    total_companies: int = 0
    total_jobs: int = 0
