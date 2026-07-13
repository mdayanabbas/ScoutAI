import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from app.discovery.sources.himalayas.models import HimalayasJobPayload
from app.jobs.job_source_detector import normalize_job_url
from app.matching.role_matcher import TargetRoleMatcher
from app.utils.enums import RemoteType, RoleCategory
from app.utils.text import normalize_text, normalize_title, repair_mojibake


@dataclass(frozen=True)
class ParsedHimalayasJob:
    accepted: bool
    rejection_reason: str | None
    source_item_id: str
    title: str
    normalized_title: str
    company_name: str
    company_slug: str | None
    description: str | None
    excerpt: str | None
    source_url: str | None
    role_category: str
    remote_eligibility: str
    remote_type: str
    seniority: str | None
    employment_type: str | None
    experience_min: int | None
    experience_max: int | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    salary_text: str | None
    published_at: datetime | None
    expiry_at: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class HimalayasJobParser:
    def __init__(self) -> None:
        self.role_matcher = TargetRoleMatcher()

    def parse(self, payload: HimalayasJobPayload, *, now: datetime | None = None) -> ParsedHimalayasJob:
        current = now or datetime.now(timezone.utc)
        title = normalize_text(payload.title) or ""
        company_name = normalize_text(payload.company_name) or "Unknown Company"
        source_item_id = normalize_text(payload.guid) or _fallback_identity(payload)
        excerpt = normalize_text(payload.excerpt)
        description = _html_to_text(payload.description_html) or excerpt
        source_url = _safe_url(payload.application_link)
        role_category, role_reason = _role_category(title, description)
        remote_eligibility, remote_type, remote_reason = _remote(payload)
        seniority, seniority_reason = _seniority(payload.seniority, title)
        experience_min, experience_max = _experience(description or "")
        employment_type = _employment_type(payload.employment_type)
        salary_min, salary_max, salary_text = _salary(payload)
        rejection_reason = None
        if not title or not source_item_id:
            rejection_reason = "invalid_provider_record"
        elif source_url is None:
            rejection_reason = "invalid_application_url"
        elif payload.expiry_at and payload.expiry_at < current:
            rejection_reason = "rejected_expired"
        elif role_reason == "unrelated_role":
            rejection_reason = "rejected_role"
        elif seniority_reason == "senior_title_or_level":
            rejection_reason = "rejected_seniority"
        elif experience_min is not None and experience_min >= 5:
            rejection_reason = "rejected_experience"
        elif remote_eligibility == "remote_country_restricted":
            rejection_reason = "rejected_country_restriction"
        elif remote_eligibility == "onsite":
            rejection_reason = "rejected_onsite"
        elif remote_eligibility == "hybrid":
            rejection_reason = "rejected_hybrid"

        metadata = {
            "companySlug": payload.company_slug,
            "employmentType": payload.employment_type,
            "seniority": payload.seniority,
            "locationRestrictions": [_restriction_dict(item) for item in payload.location_restrictions] if payload.location_restrictions is not None else None,
            "timezoneRestrictions": payload.timezone_restrictions or [],
            "categories": payload.categories,
            "parentCategories": payload.parent_categories,
            "salaryPeriod": payload.salary_period,
            "publishedAt": payload.published_at.isoformat() if payload.published_at else None,
            "expiryAt": payload.expiry_at.isoformat() if payload.expiry_at else None,
        }
        return ParsedHimalayasJob(
            accepted=rejection_reason is None,
            rejection_reason=rejection_reason,
            source_item_id=source_item_id,
            title=title,
            normalized_title=normalize_title(title) or title.lower(),
            company_name=company_name,
            company_slug=normalize_text(payload.company_slug),
            description=description,
            excerpt=excerpt,
            source_url=source_url,
            role_category=role_category,
            remote_eligibility=remote_eligibility,
            remote_type=remote_type,
            seniority=seniority,
            employment_type=employment_type,
            experience_min=experience_min,
            experience_max=experience_max,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=(payload.currency or "").upper() or None,
            salary_text=salary_text,
            published_at=payload.published_at,
            expiry_at=payload.expiry_at,
            metadata={key: value for key, value in metadata.items() if _present(value)},
            evidence={
                "role_reason": role_reason,
                "seniority_reason": seniority_reason,
                "remote_reason": remote_reason,
            },
            warnings=[
                warning
                for warning in (
                    f"published_at:{payload.published_at_parse_error}" if payload.published_at_parse_error else None,
                    f"expiry_at:{payload.expiry_at_parse_error}" if payload.expiry_at_parse_error else None,
                )
                if warning
            ],
        )


def _html_to_text(value: str | None) -> str | None:
    if not value:
        return None
    soup = BeautifulSoup(repair_mojibake(value) or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return normalize_text(soup.get_text("\n"))


def _safe_url(value: str | None) -> str | None:
    normalized = normalize_job_url(value)
    return normalized.canonical_url if normalized.valid else None


def _role_category(title: str, description: str | None) -> tuple[str, str]:
    lowered = title.lower()
    if _excluded_role(lowered, description or ""):
        return RoleCategory.OTHER.value, "unrelated_role"
    if "solutions engineer" in lowered and re.search(r"forward deployed|deployment|customer deployment", description or "", re.I):
        return RoleCategory.FORWARD_DEPLOYED_ENGINEER.value, "fde_context"
    if "forward deployed" in lowered or re.search(r"\bfde\b", lowered):
        return RoleCategory.FORWARD_DEPLOYED_ENGINEER.value, "target_role"
    if re.search(r"\b(ai|llm|genai|generative ai|applied ai)\b", lowered) and "engineer" in lowered:
        return RoleCategory.AI_ENGINEER.value, "target_role"
    if "machine learning engineer" in lowered or re.search(r"\bml engineer\b", lowered):
        return RoleCategory.ML_ENGINEER.value, "target_role"
    if "backend engineer" in lowered:
        return RoleCategory.BACKEND_ENGINEER.value, "adjacent_role"
    if "full stack" in lowered or "full-stack" in lowered:
        return RoleCategory.FULL_STACK_ENGINEER.value, "adjacent_role"
    if "product engineer" in lowered:
        return RoleCategory.PRODUCT_ENGINEER.value, "adjacent_role"
    if "software engineer" in lowered or "software development engineer" in lowered or lowered in {"sde", "swe"}:
        return RoleCategory.SOFTWARE_ENGINEER.value, "target_role"
    if "applied engineer" in lowered or "ai platform engineer" in lowered or "ml infrastructure engineer" in lowered:
        return RoleCategory.SOFTWARE_ENGINEER.value, "adjacent_role"
    return RoleCategory.OTHER.value, "unrelated_role"


def _excluded_role(title: str, description: str) -> bool:
    if "solutions engineer" in title and not re.search(r"forward deployed|deployment|customer deployment", description, re.I):
        return True
    blocked = (
        "electrical engineer",
        "robotics engineer",
        "perception engineer",
        "mechanical engineer",
        "manufacturing engineer",
        "test engineer",
        "sales engineer",
        "developer advocate",
        "product manager",
        "account executive",
        "marketing",
        "operations",
        "machinist",
    )
    if "embedded software engineer" in title:
        return False
    return any(item in title for item in blocked)


def _remote(payload: HimalayasJobPayload) -> tuple[str, str, str]:
    restrictions = payload.location_restrictions
    if restrictions is None:
        return "remote_eligibility_unclear", RemoteType.REMOTE_REGION.value, "missing_location_restrictions"
    if len(restrictions) == 0:
        return "work_from_anywhere", RemoteType.REMOTE_WORLDWIDE.value, "empty_location_restrictions"
    countries = {str(item.alpha2 or "").upper() for item in restrictions if item.alpha2}
    if "IN" in countries:
        return "remote_india_eligible", RemoteType.REMOTE_COUNTRY.value, "india_location_restriction"
    if countries and "IN" not in countries:
        return "remote_country_restricted", RemoteType.REMOTE_COUNTRY.value, "country_restriction_excludes_india"
    return "remote_eligibility_unclear", RemoteType.REMOTE_REGION.value, "unparsed_location_restrictions"


def _seniority(values: list[str], title: str) -> tuple[str | None, str]:
    title_text = title.lower()
    if re.search(r"\b(staff|principal|lead|manager|director|executive|head of|vp|vice president)\b", title_text):
        return _seniority_label(values), "senior_title_or_level"
    if re.search(r"\bsenior\b", title_text):
        return _seniority_label(values), "senior_title_or_level"
    lowered = {value.lower() for value in values}
    if lowered & {"intern", "internship"} or re.search(r"\b(intern|internship)\b", title_text):
        return _seniority_label(values) or "internship", "entry_level"
    if lowered & {"entry-level", "entry level", "junior"} or re.search(r"\b(entry|entry level|junior|new grad|graduate|associate|engineer i)\b", title_text):
        return _seniority_label(values) or "entry_level", "entry_level"
    if "mid-level" in lowered or "mid level" in lowered:
        return _seniority_label(values), "mid_level"
    if lowered and lowered <= {"senior", "manager", "director", "executive"}:
        return _seniority_label(values), "senior_title_or_level"
    return _seniority_label(values), "open_or_missing"


def _seniority_label(values: list[str]) -> str | None:
    return ", ".join(values) if values else None


def _experience(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"\b(\d+)\s*(?:\+|to|-)\s*(\d+)?\s+years?", text, re.I)
    if not match:
        return None, None
    first = int(match.group(1))
    second = int(match.group(2)) if match.group(2) else None
    return first, second


def _employment_type(value: str | None) -> str | None:
    text = str(value or "").lower().replace("-", " ")
    if "full" in text:
        return "full_time"
    if "part" in text:
        return "part_time"
    if "contract" in text:
        return "contract"
    if "intern" in text:
        return "internship"
    if "temporary" in text:
        return "temporary"
    if "volunteer" in text:
        return "volunteer"
    return "other" if text.strip() else None


def _salary(payload: HimalayasJobPayload) -> tuple[int | None, int | None, str | None]:
    period = str(payload.salary_period or "annual").lower()
    parts = []
    if payload.minimum_salary is not None:
        parts.append(str(payload.minimum_salary))
    if payload.maximum_salary is not None and payload.maximum_salary != payload.minimum_salary:
        parts.append(str(payload.maximum_salary))
    salary_text = " - ".join(parts)
    if salary_text and payload.currency:
        salary_text = f"{payload.currency.upper()} {salary_text}"
    if salary_text and payload.salary_period:
        salary_text = f"{salary_text} / {payload.salary_period}"
    if period in {"year", "yearly", "annual", "annually", "per year"}:
        return payload.minimum_salary, payload.maximum_salary, salary_text or None
    return None, None, salary_text or None


def _restriction_dict(item: Any) -> dict[str, str | None]:
    return {"alpha2": item.alpha2, "name": item.name, "slug": item.slug}


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != []


def _fallback_identity(payload: HimalayasJobPayload) -> str:
    return "|".join(
        part
        for part in (
            normalize_title(payload.company_slug or payload.company_name),
            normalize_title(payload.title),
            normalize_text(payload.application_link),
        )
        if part
    )
