import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.discovery.sources.remotive.parser import ParsedRemotiveJob
from app.utils.enums import RemoteType, RoleCategory
from app.utils.text import normalize_title


class RemotiveTargetJobFilter:
    def evaluate(self, parsed: ParsedRemotiveJob, *, max_age_days: int = 45, now: datetime | None = None) -> ParsedRemotiveJob:
        current = now or datetime.now(timezone.utc)
        text = "\n".join(part for part in (parsed.title, parsed.location, parsed.description, parsed.category) if part)
        role_category, role_match = _role(parsed.title, text)
        remote_eligibility, remote_type, remote_reason = _remote(parsed.location, parsed.description)
        seniority, seniority_reason = _seniority(parsed.title, parsed.description)
        experience_min, experience_max = _experience(parsed.description or "")
        rejection = None
        if parsed.source_url is None:
            rejection = "rejected_invalid_url"
        elif not parsed.company_name:
            rejection = "rejected_missing_company_identity"
        elif parsed.published_at and parsed.published_at < current - timedelta(days=max_age_days):
            rejection = "rejected_stale_listing"
        elif role_match == "rejected":
            rejection = "rejected_role"
        elif seniority_reason == "senior":
            rejection = "rejected_seniority"
        elif experience_min is not None and experience_min >= 4:
            rejection = "rejected_experience"
        elif remote_eligibility == "remote_country_restricted":
            rejection = "rejected_country_restriction"
        elif remote_eligibility == "hybrid":
            rejection = "rejected_hybrid"
        elif remote_eligibility == "onsite":
            rejection = "rejected_onsite"
        return replace(
            parsed,
            accepted=rejection is None,
            rejection_reason=rejection,
            role_category=role_category,
            role_match_type=role_match,
            remote_eligibility=remote_eligibility,
            remote_type=remote_type,
            seniority=seniority,
            experience_min=experience_min,
            experience_max=experience_max,
            evidence={
                **parsed.evidence,
                "role_match": role_match,
                "seniority_reason": seniority_reason,
                "remote_reason": remote_reason,
                "experience_min": experience_min,
                "experience_max": experience_max,
            },
        )


def _role(title: str, text: str) -> tuple[str, str]:
    value = normalize_title(title) or ""
    haystack = normalize_title(text) or ""
    blocked = (
        "electrical engineer",
        "mechanical engineer",
        "robotics engineer",
        "perception engineer",
        "manufacturing engineer",
        "test engineer",
        "qa engineer",
        "sales engineer",
        "developer advocate",
        "account executive",
        "product manager",
        "project manager",
        "marketing",
        "customer support",
        "operations",
        "recruiter",
        "data entry",
    )
    if any(term in value for term in blocked):
        return RoleCategory.OTHER.value, "rejected"
    if "solutions engineer" in value and not re.search(r"forward deployed|fde|customer deployment|deployment with customers", haystack):
        return RoleCategory.OTHER.value, "rejected"
    if "forward deployed" in value or value == "fde" or "forward-deployed" in title.lower():
        return RoleCategory.FORWARD_DEPLOYED_ENGINEER.value, "target"
    if re.search(r"\b(ai|artificial intelligence|applied ai|generative ai|genai|llm)\b", value) and "engineer" in value:
        return RoleCategory.AI_ENGINEER.value, "target"
    if "machine learning engineer" in value or "ml engineer" in value or value == "mle":
        return RoleCategory.ML_ENGINEER.value, "target"
    if value in {"swe", "sde"} or "software engineer" in value or "software development engineer" in value or "software developer" in value:
        return RoleCategory.SOFTWARE_ENGINEER.value, "target"
    if "backend engineer" in value or "backend developer" in value or "backend ai engineer" in value:
        return RoleCategory.BACKEND_ENGINEER.value, "adjacent"
    if "full stack engineer" in value or "full-stack engineer" in value:
        return RoleCategory.FULL_STACK_ENGINEER.value, "adjacent"
    if "product engineer" in value:
        return RoleCategory.PRODUCT_ENGINEER.value, "adjacent"
    if "ai platform engineer" in value or "ml infrastructure engineer" in value or "applied engineer" in value:
        return RoleCategory.SOFTWARE_ENGINEER.value, "adjacent"
    return RoleCategory.OTHER.value, "rejected"


def _remote(location: str | None, description: str | None) -> tuple[str, str, str]:
    provider = (location or "").lower()
    focused = "\n".join(part for part in (location, description) if part).lower()
    if _has(focused, r"\b(hybrid|office based|on-site|onsite|in person|in-person|relocation required|remote unavailable)\b") and not _has(focused, r"annual offsites|optional office|optional coworking|customer-site visits"):
        return ("hybrid", RemoteType.HYBRID.value, "hybrid") if "hybrid" in focused else ("onsite", RemoteType.ONSITE.value, "onsite")
    if _has(provider, r"excluding india|worldwide excluding india"):
        return "remote_country_restricted", RemoteType.REMOTE_COUNTRY.value, "excludes_india"
    if _has(provider, r"worldwide|anywhere|anywhere in the world|global|all countries"):
        return "work_from_anywhere", RemoteType.REMOTE_WORLDWIDE.value, "provider_worldwide"
    if _has(provider, r"\bindia\b|asia-pacific|asia pacific|\bapac\b|\basia\b"):
        return "remote_india_eligible", RemoteType.REMOTE_REGION.value, "provider_india_or_apac"
    if _has(provider, r"\b(usa|us|united states|canada|north america|uk|united kingdom|eu|europe|emea|latam|australia|new zealand)\b"):
        return "remote_country_restricted", RemoteType.REMOTE_COUNTRY.value, "provider_restricted"
    if _has(focused, r"worldwide|anywhere in the world|work from anywhere"):
        return "work_from_anywhere", RemoteType.REMOTE_WORLDWIDE.value, "description_worldwide"
    if _has(focused, r"\bindia\b|\bapac\b|\basia\b"):
        return "remote_india_eligible", RemoteType.REMOTE_REGION.value, "description_india_or_apac"
    return "remote_eligibility_unclear", RemoteType.REMOTE_REGION.value, "remote_scope_unclear"


def _seniority(title: str, description: str | None) -> tuple[str | None, str]:
    title_key = (normalize_title(title) or "").lower()
    if _has(title_key, r"\b(senior|staff|principal|lead|manager|director|head of|vp|vice president|executive)\b"):
        return "senior", "senior"
    if _has(title_key, r"\b(intern|internship|entry level|entry-level|junior|graduate|new grad|associate|engineer i)\b"):
        return "entry_level", "entry"
    exp_min, _ = _experience(description or "")
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
