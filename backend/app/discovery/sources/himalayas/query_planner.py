import re
from dataclasses import dataclass, field
from typing import Any


DEFAULT_QUERIES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Forward Deployed Engineer",
    "Software Engineer",
    "Software Development Engineer",
]
PRIORITY_QUERIES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Forward Deployed Engineer",
    "Software Engineer",
    "Applied AI Engineer",
    "LLM Engineer",
    "Software Development Engineer",
    "Generative AI Engineer",
    "Forward Deployed AI Engineer",
]
ALIAS_TO_CANONICAL = {
    "ml engineer": "Machine Learning Engineer",
    "swe": "Software Engineer",
    "sde": "Software Engineer",
    "software development engineer": "Software Development Engineer",
    "forward deployed ai engineer": "Forward Deployed AI Engineer",
    "generative ai engineer": "Generative AI Engineer",
    "applied ai engineer": "Applied AI Engineer",
    "llm engineer": "LLM Engineer",
    "ai engineer": "AI Engineer",
}
EXCLUDED_QUERY_TERMS = {
    "sales",
    "marketing",
    "account executive",
    "product manager",
    "electrical engineer",
    "mechanical engineer",
    "robotics engineer",
    "perception engineer",
    "machinist",
}
CATEGORY_TO_QUERY = {
    "ai_engineer": "AI Engineer",
    "ml_engineer": "Machine Learning Engineer",
    "machine_learning_engineer": "Machine Learning Engineer",
    "forward_deployed_engineer": "Forward Deployed Engineer",
    "software_engineer": "Software Engineer",
}


@dataclass(frozen=True)
class HimalayasQueryPass:
    query: str
    query_type: str
    country: str | None = None
    worldwide: bool | None = None
    exclude_worldwide: bool | None = None
    sort: str = "recent"


@dataclass(frozen=True)
class HimalayasQueryPlan:
    queries: list[str]
    passes: list[HimalayasQueryPass]
    generated_from_profile: bool
    role_aliases: dict[str, str] = field(default_factory=dict)
    country_queries: list[str] = field(default_factory=list)
    worldwide_queries: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class HimalayasTargetedQueryPlanner:
    def build_plan(self, profile: Any | None, *, max_queries: int) -> HimalayasQueryPlan:
        raw_titles = list(getattr(profile, "target_titles_json", []) or []) if profile is not None else []
        raw_categories = list(getattr(profile, "target_role_categories_json", []) or []) if profile is not None else []
        generated_from_profile = bool(raw_titles or raw_categories)
        aliases: dict[str, str] = {}
        candidates: list[str] = []
        for title in raw_titles:
            normalized = _normalize(title)
            if not normalized or _excluded(normalized):
                continue
            canonical = ALIAS_TO_CANONICAL.get(normalized) or _title_case(normalized)
            aliases[str(title)] = canonical
            candidates.append(canonical)
        for category in raw_categories:
            query = CATEGORY_TO_QUERY.get(str(category))
            if query:
                candidates.append(query)
        if not candidates:
            candidates.extend(DEFAULT_QUERIES)
        ordered = _ordered_unique(candidates)
        queries = ordered
        warnings = []
        passes: list[HimalayasQueryPass] = []
        for query in queries:
            if len(passes) >= max_queries:
                warnings.append("himalayas_query_cap_applied")
                break
            passes.append(HimalayasQueryPass(query=query, query_type="worldwide", worldwide=True))
            if len(passes) >= max_queries:
                warnings.append("himalayas_query_cap_applied")
                break
            passes.append(HimalayasQueryPass(query=query, query_type="india", country="IN", exclude_worldwide=False))
        planned_queries = _queries_from_passes(passes)
        return HimalayasQueryPlan(
            queries=planned_queries,
            passes=passes,
            generated_from_profile=generated_from_profile,
            role_aliases=aliases,
            country_queries=[item.query for item in passes if item.query_type == "india"],
            worldwide_queries=[item.query for item in passes if item.query_type == "worldwide"],
            warnings=warnings,
        )


def _ordered_unique(values: list[str]) -> list[str]:
    deduped = []
    seen: set[str] = set()
    for priority in PRIORITY_QUERIES:
        if priority not in values:
            continue
        key = _canonical_key(priority)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(priority)
    for value in values:
        key = _canonical_key(value)
        if key not in seen:
            seen.add(key)
            deduped.append(value)
    return deduped


def _queries_from_passes(passes: list[HimalayasQueryPass]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in passes:
        if item.query in seen:
            continue
        seen.add(item.query)
        result.append(item.query)
    return result


def _canonical_key(value: str) -> str:
    normalized = _normalize(value)
    if normalized in {"swe", "sde"}:
        return "software engineer"
    return normalized


def _normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9+#/]+", " ", str(value or "").lower()).strip()


def _title_case(value: str) -> str:
    return " ".join(part.upper() if part in {"ai", "ml", "llm", "sde", "swe"} else part.capitalize() for part in value.split())


def _excluded(value: str) -> bool:
    return any(term == value or term in value for term in EXCLUDED_QUERY_TERMS)
