import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.discovery.sources.we_work_remotely.models import WWRFeedItem
from app.discovery.sources.we_work_remotely.normalizer import parse_salary
from app.utils.enums import RemoteType, RoleCategory
from app.utils.text import normalize_title


@dataclass(frozen=True)
class WWRFilterResult:
    accepted: bool
    rejection_reason: str | None
    role_category: str
    role_match_type: str
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
    evidence: dict = field(default_factory=dict)


class WWRTargetJobFilter:
    def evaluate(self, item: WWRFeedItem, *, max_age_days: int = 45, now: datetime | None = None) -> WWRFilterResult:
        current = now or datetime.now(timezone.utc)
        title = item.role_title or item.title or ""
        text = "\n".join(part for part in (title, item.region_text, item.description_text, " ".join(item.categories)) if part)
        role_category, role_match = _role(title, text)
        remote_eligibility, remote_type, remote_reason = _remote(text)
        seniority, seniority_reason = _seniority(title, text)
        exp_min, exp_max = _experience(text)
        salary_min, salary_max, currency, salary_text = parse_salary(item.salary_text or item.description_text)
        rejection = None
        if not item.link:
            rejection = "rejected_invalid_url"
        elif not item.company_name:
            rejection = "rejected_missing_company_identity"
        elif item.published_at and item.published_at < current - timedelta(days=max_age_days):
            rejection = "rejected_stale_listing"
        elif role_match == "rejected":
            rejection = "rejected_role"
        elif seniority_reason == "senior":
            rejection = "rejected_seniority"
        elif exp_min is not None and exp_min >= 4:
            rejection = "rejected_experience"
        elif remote_eligibility == "remote_country_restricted":
            rejection = "rejected_country_restriction"
        elif remote_eligibility == "hybrid":
            rejection = "rejected_hybrid"
        elif remote_eligibility == "onsite":
            rejection = "rejected_onsite"
        return WWRFilterResult(
            accepted=rejection is None,
            rejection_reason=rejection,
            role_category=role_category,
            role_match_type=role_match,
            remote_eligibility=remote_eligibility,
            remote_type=remote_type,
            seniority=seniority,
            employment_type=item.employment_type,
            experience_min=exp_min,
            experience_max=exp_max,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=currency,
            salary_text=salary_text or item.salary_text,
            evidence={"remote_reason": remote_reason, "seniority_reason": seniority_reason, "role_match": role_match},
        )


def _role(title: str, text: str) -> tuple[str, str]:
    value = normalize_title(title) or ""
    haystack = normalize_title(text) or ""
    if "solutions engineer" in value and not re.search(r"forward deployed|customer deployment|embed with customers|deployment with customers", haystack):
        return RoleCategory.OTHER.value, "rejected"
    blocked = ("electrical engineer", "mechanical engineer", "robotics engineer", "perception engineer", "manufacturing engineer", "test engineer", "qa engineer", "sales engineer", "developer advocate", "account executive", "product manager", "marketing", "customer support", "operations", "data entry", "trader")
    if any(term in value for term in blocked):
        return RoleCategory.OTHER.value, "rejected"
    if "forward deployed" in value or value == "fde" or "forward deployed" in haystack:
        return RoleCategory.FORWARD_DEPLOYED_ENGINEER.value, "target"
    if re.search(r"\b(ai|genai|llm|artificial intelligence|applied ai)\b", value) and "engineer" in value:
        return RoleCategory.AI_ENGINEER.value, "target"
    if "machine learning engineer" in value or "ml engineer" in value or value == "mle":
        return RoleCategory.ML_ENGINEER.value, "target"
    if "software engineer" in value or "software development engineer" in value or value in {"sde", "swe", "software developer"}:
        return RoleCategory.SOFTWARE_ENGINEER.value, "target"
    adjacent = ("backend engineer", "backend developer", "full stack engineer", "full-stack engineer", "product engineer", "ai platform engineer", "ml infrastructure engineer", "applied engineer", "backend ai engineer")
    if any(term in value for term in adjacent):
        return RoleCategory.BACKEND_ENGINEER.value if "backend" in value else RoleCategory.SOFTWARE_ENGINEER.value, "adjacent"
    return RoleCategory.OTHER.value, "rejected"


def _remote(text: str) -> tuple[str, str, str]:
    value = text.lower()
    if _has(value, r"\b(hybrid|office based|on-site|onsite|in person|in-person|must relocate|remote not available|must work from our office)\b") and not _has(value, r"optional office|annual company offsite|optional coworking"):
        return "hybrid" if "hybrid" in value else "onsite", RemoteType.HYBRID.value if "hybrid" in value else RemoteType.ONSITE.value, "onsite_or_hybrid"
    if _has(value, r"worldwide excluding india|excluding india"):
        return "remote_country_restricted", RemoteType.REMOTE_COUNTRY.value, "excludes_india"
    if _has(value, r"anywhere in the world|worldwide|work from anywhere|remote worldwide|globally remote"):
        return "work_from_anywhere", RemoteType.REMOTE_WORLDWIDE.value, "worldwide"
    if _has(value, r"\bindia\b|apac including india|asia including india|asia only|\bapac\b"):
        return "remote_india_eligible", RemoteType.REMOTE_REGION.value, "india_or_asia"
    if _has(value, r"us only|usa only|united states only|canada only|north america only|americas only|latam only|europe only|eu only|emea only|uk only|australia only|new zealand only"):
        return "remote_country_restricted", RemoteType.REMOTE_COUNTRY.value, "region_excludes_india"
    if _has(value, r"\bremote\b"):
        return "remote_eligibility_unclear", RemoteType.REMOTE_REGION.value, "remote_without_scope"
    return "remote_eligibility_unclear", RemoteType.REMOTE_REGION.value, "wwr_remote_feed"


def _seniority(title: str, text: str) -> tuple[str | None, str]:
    title_key = (normalize_title(title) or "").lower()
    if _has(title_key, r"\b(senior|staff|principal|lead|manager|director|executive|head of|vp|vice president)\b"):
        return "senior", "senior"
    if _has(title_key, r"\b(intern|internship|entry level|entry-level|junior|new grad|graduate|associate|engineer i)\b"):
        return "entry_level", "entry"
    exp_min, _ = _experience(text)
    if exp_min is not None and exp_min >= 5:
        return "senior", "senior"
    if exp_min == 4:
        return "mid_level", "senior"
    if exp_min == 3:
        return "mid_level", "stretch"
    return None, "open"


def _experience(text: str) -> tuple[int | None, int | None]:
    scrubbed = re.sub(r"\$\s?\d[\d,]*(?:k)?", "", text.lower())
    match = re.search(r"\b(?:at least\s*)?(\d+)\s*(?:\+|to|-|–)?\s*(\d+)?\s+years?", scrubbed)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2)) if match.group(2) else None


def _has(value: str, pattern: str) -> bool:
    return bool(re.search(pattern, value, re.I))
