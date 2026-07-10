from pydantic import BaseModel


class JobSourceDetectionRead(BaseModel):
    source_type: str
    canonical_url: str | None = None
    normalized_domain: str | None = None
    provider: str | None = None
    company_slug: str | None = None
    job_identifier: str | None = None
    board_slug: str | None = None
    is_first_party: bool
    supported: bool
    confidence: float
    reason: str
