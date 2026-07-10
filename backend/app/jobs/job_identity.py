from dataclasses import dataclass

from app.jobs.job_source_detector import normalize_job_url


@dataclass(frozen=True)
class JobIdentity:
    company_id: str | None
    canonical_job_url: str | None
    normalized_title: str | None
    identity_key: str | None
    identity_strategy: str


def build_job_identity(
    *,
    company_id: str | None,
    job_url: str | None,
    normalized_title: str | None,
) -> JobIdentity:
    if not company_id:
        return JobIdentity(
            company_id=company_id,
            canonical_job_url=None,
            normalized_title=normalized_title,
            identity_key=None,
            identity_strategy="insufficient_identity",
        )

    normalized = normalize_job_url(job_url)
    if normalized.valid and normalized.canonical_url:
        return JobIdentity(
            company_id=company_id,
            canonical_job_url=normalized.canonical_url,
            normalized_title=normalized_title,
            identity_key=f"company:{company_id}:url:{normalized.canonical_url}",
            identity_strategy="company_and_canonical_url",
        )

    title = (normalized_title or "").strip().lower()
    if title:
        return JobIdentity(
            company_id=company_id,
            canonical_job_url=None,
            normalized_title=title,
            identity_key=f"company:{company_id}:title:{title}",
            identity_strategy="company_and_title",
        )

    return JobIdentity(
        company_id=company_id,
        canonical_job_url=None,
        normalized_title=None,
        identity_key=None,
        identity_strategy="insufficient_identity",
    )
