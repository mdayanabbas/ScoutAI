from typing import Literal

from pydantic import BaseModel

from app.schemas.job import JobRead

DiscoveryJobIngestionAction = Literal["created", "already_exists", "skipped", "failed"]


class DiscoveryJobIngestionResult(BaseModel):
    candidate_id: str
    company_id: str | None = None
    job_id: str | None = None
    action: DiscoveryJobIngestionAction
    message: str
    job: JobRead | None = None


class DiscoveryRunJobIngestionResult(BaseModel):
    discovery_run_id: str
    candidates_examined: int
    jobs_created: int
    jobs_existing: int
    candidates_skipped: int
    candidates_failed: int
    results: list[DiscoveryJobIngestionResult]
