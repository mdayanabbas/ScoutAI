import re
from dataclasses import dataclass, field
from typing import Any

from app.discovery.sources.remotive.constants import REMOTIVE_SOFTWARE_CATEGORY


DEFAULT_SEARCHES = ["AI Engineer", "Machine Learning Engineer", "Forward Deployed Engineer", "LLM Engineer", "Software Engineer"]
PRIORITY_SEARCHES = ["AI Engineer", "Machine Learning Engineer", "Forward Deployed Engineer", "LLM Engineer", "Software Engineer"]
ALIAS_TO_CANONICAL = {
    "ai engineer": "AI Engineer",
    "applied ai engineer": "AI Engineer",
    "generative ai engineer": "AI Engineer",
    "genai engineer": "AI Engineer",
    "artificial intelligence engineer": "AI Engineer",
    "llm engineer": "LLM Engineer",
    "machine learning engineer": "Machine Learning Engineer",
    "ml engineer": "Machine Learning Engineer",
    "mle": "Machine Learning Engineer",
    "applied machine learning engineer": "Machine Learning Engineer",
    "forward deployed engineer": "Forward Deployed Engineer",
    "forward deployed ai engineer": "Forward Deployed Engineer",
    "fde": "Forward Deployed Engineer",
    "software engineer": "Software Engineer",
    "software development engineer": "Software Engineer",
    "software developer": "Software Engineer",
    "sde": "Software Engineer",
    "swe": "Software Engineer",
}
CATEGORY_TO_SEARCH = {
    "ai_engineer": "AI Engineer",
    "ml_engineer": "Machine Learning Engineer",
    "software_engineer": "Software Engineer",
    "forward_deployed_engineer": "Forward Deployed Engineer",
}


@dataclass(frozen=True)
class RemotiveQueryRequest:
    request_type: str
    category: str | None = None
    search_term: str | None = None
    limit: int | None = None


@dataclass(frozen=True)
class RemotiveQueryPlan:
    requests: list[RemotiveQueryRequest]
    generated_from_profile: bool
    canonical_target_roles: list[str]
    warnings: list[str] = field(default_factory=list)


class RemotiveTargetedQueryPlanner:
    def build_plan(
        self,
        profile: Any | None,
        *,
        max_requests: int,
        limit: int,
        software_category_enabled: bool = True,
    ) -> RemotiveQueryPlan:
        raw_titles = list(getattr(profile, "target_titles_json", []) or []) if profile is not None else []
        raw_categories = list(getattr(profile, "target_role_categories_json", []) or []) if profile is not None else []
        generated_from_profile = bool(raw_titles or raw_categories)
        canonical_roles = _canonical_roles(raw_titles, raw_categories)
        if not canonical_roles:
            canonical_roles = DEFAULT_SEARCHES[:]

        requests: list[RemotiveQueryRequest] = []
        warnings: list[str] = []
        if software_category_enabled:
            requests.append(RemotiveQueryRequest("category", category=REMOTIVE_SOFTWARE_CATEGORY, limit=limit))
        for role in _ordered_roles(canonical_roles):
            if len(requests) >= max_requests:
                warnings.append("remotive_request_cap_applied")
                break
            requests.append(RemotiveQueryRequest("search", search_term=role, limit=limit))
        if len(requests) > max_requests:
            requests = requests[:max_requests]
            warnings.append("remotive_request_cap_applied")
        return RemotiveQueryPlan(
            requests=requests,
            generated_from_profile=generated_from_profile,
            canonical_target_roles=_ordered_roles(canonical_roles),
            warnings=warnings,
        )


def _canonical_roles(titles: list[Any], categories: list[Any]) -> list[str]:
    roles: list[str] = []
    for title in titles:
        normalized = _normalize(title)
        canonical = ALIAS_TO_CANONICAL.get(normalized)
        if canonical:
            roles.append(canonical)
    for category in categories:
        canonical = CATEGORY_TO_SEARCH.get(str(category))
        if canonical:
            roles.append(canonical)
    return _dedupe(roles)


def _ordered_roles(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for priority in PRIORITY_SEARCHES:
        if priority in values and priority not in seen:
            result.append(priority)
            seen.add(priority)
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _dedupe(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9+#/]+", " ", str(value or "").lower()).strip()
