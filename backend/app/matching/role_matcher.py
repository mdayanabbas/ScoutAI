import re
from dataclasses import dataclass, field
from typing import Any


TARGET_ROLE_ALIASES = {
    "ai_engineer": {
        "ai engineer",
        "artificial intelligence engineer",
        "applied ai engineer",
        "generative ai engineer",
        "genai engineer",
        "llm engineer",
        "ai software engineer",
    },
    "machine_learning_engineer": {
        "machine learning engineer",
        "ml engineer",
        "mle",
        "applied machine learning engineer",
    },
    "forward_deployed_engineer": {
        "forward deployed engineer",
        "forward deployed ai engineer",
        "forward-deployed engineer",
        "fde",
    },
    "software_engineer": {
        "software engineer",
        "software development engineer",
        "software developer",
        "sde",
        "swe",
    },
}
ADJACENT_ROLES = {
    "backend engineer",
    "full stack engineer",
    "full-stack engineer",
    "product engineer",
    "applied engineer",
    "ai backend engineer",
    "ai platform engineer",
    "embedded software engineer",
    "robotics software engineer",
    "ml infrastructure engineer",
    "ai solutions engineer",
}
EXCLUDED_ENGINEERING = {
    "electrical engineer",
    "robotics engineer",
    "perception engineer",
    "mechanical engineer",
    "manufacturing engineer",
    "machinist",
    "shop manager",
    "sales engineer",
    "solutions engineer",
    "civil engineer",
    "hardware engineer",
    "embedded engineer",
    "test engineer",
}


@dataclass(frozen=True)
class RoleMatchResult:
    matched: bool
    canonical_role: str | None
    match_type: str
    score: int
    confidence: float
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)
    reason: str = "no_target_role_match"


class TargetRoleMatcher:
    def match(self, job: Any, profile: Any | None = None) -> RoleMatchResult:
        title = _normalize(getattr(job, "title", None))
        raw_category = getattr(job, "role_category", "") or ""
        category = str(getattr(raw_category, "value", raw_category))
        description = _normalize(getattr(job, "description", None))[:2000]
        haystack = " ".join(item for item in (title, category.replace("_", " "), description) if item)
        excluded_titles = {_normalize(item) for item in getattr(profile, "excluded_titles_json", []) or []}
        excluded_categories = {str(item) for item in getattr(profile, "excluded_role_categories_json", []) or []}
        if category in excluded_categories:
            return _result(False, None, "excluded", 0, 1.0, negative=[f"excluded_category:{category}"], reason="excluded_role_category")
        if any(item and (item == title or item in title) for item in excluded_titles):
            return _result(False, None, "excluded", 0, 1.0, negative=["excluded_title"], reason="excluded_title")
        if _is_excluded_title(title):
            return _result(False, None, "excluded", 0, 0.95, negative=[title], reason="unrelated_engineering_role")
        for canonical, aliases in TARGET_ROLE_ALIASES.items():
            if title in aliases:
                match_type = "exact" if title.replace("-", " ") == canonical.replace("_", " ") else "alias"
                return _result(True, canonical, match_type, 100 if match_type == "exact" else 95, 0.98, positive=[title], reason="target_role")
            if any(_phrase_present(alias, title) for alias in aliases if len(alias) > 3):
                return _result(True, canonical, "alias", 95, 0.92, positive=[title], reason="target_role_alias")
        if "deployment engineer" in title and "forward" in haystack:
            return _result(True, "forward_deployed_engineer", "alias", 90, 0.85, positive=["deployment_forward_context"], reason="fde_context")
        for adjacent in ADJACENT_ROLES:
            if adjacent in title:
                canonical = "machine_learning_engineer" if "ml infrastructure" in title else "software_engineer"
                if "ai solution" in title:
                    canonical = "ai_engineer"
                return _result(True, canonical, "adjacent", 75, 0.82, positive=[adjacent], reason="adjacent_target_role")
        if category in {"ai_engineer", "ml_engineer", "machine_learning_engineer"}:
            return _result(True, "machine_learning_engineer", "category_only", 60, 0.7, positive=[category], reason="category_only")
        if category in {"software_engineer", "forward_deployed_engineer"}:
            return _result(True, category, "category_only", 60, 0.65, positive=[category], reason="category_only")
        return _result(False, None, "no_match", 0, 0.8, negative=[title or category or "missing_role"], reason="no_target_role_match")


def _result(
    matched: bool,
    role: str | None,
    match_type: str,
    score: int,
    confidence: float,
    *,
    positive: list[str] | None = None,
    negative: list[str] | None = None,
    reason: str,
) -> RoleMatchResult:
    return RoleMatchResult(matched, role, match_type, score, confidence, positive or [], negative or [], reason)


def _normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9+#/]+", " ", str(value or "").lower()).strip()


def _phrase_present(phrase: str, title: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", title))


def _is_excluded_title(title: str) -> bool:
    if "software" in title or "firmware" in title:
        return False
    return any(excluded == title or excluded in title for excluded in EXCLUDED_ENGINEERING)
