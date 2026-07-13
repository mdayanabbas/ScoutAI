from dataclasses import dataclass, field
from typing import Any

from app.jobs.job_source_detector import normalize_job_url


@dataclass(frozen=True)
class JobActionabilityResult:
    actionable: bool
    status: str
    confidence: float
    valid_job_url: bool
    valid_apply_url: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class JobActionabilityValidator:
    CLOSED_STATUSES = {"inactive", "expired", "closed", "deleted"}

    def validate(self, job: Any) -> JobActionabilityResult:
        reasons: list[str] = []
        warnings: list[str] = []
        status = _value(getattr(job, "status", None)).lower()
        if status in self.CLOSED_STATUSES:
            return JobActionabilityResult(
                actionable=False,
                status="closed",
                confidence=0.98,
                valid_job_url=False,
                valid_apply_url=False,
                reasons=["job_status_closed"],
            )

        job_url = normalize_job_url(getattr(job, "job_url", None))
        apply_url = normalize_job_url(getattr(job, "apply_url", None))
        valid_job_url = job_url.valid
        valid_apply_url = apply_url.valid

        if not valid_job_url:
            reasons.append(f"job_url_{job_url.reason}")
        if not valid_apply_url:
            reasons.append(f"apply_url_{apply_url.reason}")
        if _value(getattr(job, "source_platform", None)).lower() == "invalid" and not valid_apply_url:
            reasons.append("source_detection_invalid")

        if not valid_job_url and not valid_apply_url:
            return JobActionabilityResult(
                actionable=False,
                status="invalid",
                confidence=0.96,
                valid_job_url=False,
                valid_apply_url=False,
                reasons=_dedupe(reasons or ["missing_actionable_url"]),
            )

        enrichment = _value(getattr(job, "enrichment_status", None)).lower()
        if enrichment in {"", "not_enriched", "pending", "unresolved", "failed"}:
            warnings.append("job_not_verified_by_enrichment")
            return JobActionabilityResult(
                actionable=True,
                status="unverified",
                confidence=0.68,
                valid_job_url=valid_job_url,
                valid_apply_url=valid_apply_url,
                reasons=_dedupe(reasons),
                warnings=warnings,
            )

        if valid_job_url and valid_apply_url:
            return JobActionabilityResult(True, "actionable", 0.95, True, True, _dedupe(reasons), warnings)

        return JobActionabilityResult(
            actionable=True,
            status="partially_actionable",
            confidence=0.82,
            valid_job_url=valid_job_url,
            valid_apply_url=valid_apply_url,
            reasons=_dedupe(reasons),
            warnings=warnings,
        )


def _value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
