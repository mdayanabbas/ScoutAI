import re
from dataclasses import dataclass, field
from typing import Any

from app.jobs.enrichment.parsers.ycombinator_job_parser import classify_role_category
from app.utils.text import normalize_title


@dataclass(frozen=True)
class HiringScopeResult:
    scope_type: str
    role_categories: list[str] = field(default_factory=list)
    department_terms: list[str] = field(default_factory=list)
    team_terms: list[str] = field(default_factory=list)
    title_terms: list[str] = field(default_factory=list)
    confidence: float = 0.0
    specific_role: bool = False
    broad_hiring: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)
    reason: str = "scope_detected"


class HiringScopeDetector:
    def detect(
        self,
        *,
        title: str | None = None,
        description: str | None = None,
        normalized_title: str | None = None,
        role_category: str | None = None,
        candidates: list[Any] | None = None,
    ) -> HiringScopeResult:
        pieces = [title, description, normalized_title, role_category]
        for candidate in candidates or []:
            pieces.extend(
                [
                    getattr(candidate, "raw_name", None),
                    getattr(candidate, "raw_description", None),
                    getattr(candidate, "normalized_description", None),
                    _payload_text(getattr(candidate, "raw_payload", None)),
                ]
            )
            for evidence in getattr(candidate, "evidence", []) or []:
                pieces.extend([getattr(evidence, "title", None), getattr(evidence, "excerpt", None)])
        text = " ".join(str(item) for item in pieces if item).lower()
        normalized = normalize_title(title or normalized_title or "")
        evidence = {"title": title, "matched_text": _bounded(text)}

        if _specific_role(normalized, text):
            category = classify_role_category(title, role_category, description)
            return HiringScopeResult(
                "specific_role",
                role_categories=[category],
                title_terms=_keywords(title),
                confidence=0.92,
                specific_role=True,
                evidence=evidence,
                reason="specific_role_detected",
            )
        if _has_any(text, ("gtm team", "go-to-market", "revenue team", "commercial team", "sales team")):
            return HiringScopeResult(
                "gtm",
                role_categories=["sales", "marketing"],
                department_terms=["gtm", "go-to-market", "revenue", "commercial", "sales", "marketing", "customer success"],
                team_terms=["gtm", "revenue", "growth", "partnerships", "customer success"],
                title_terms=["account executive", "sales", "growth", "marketing", "partnerships", "customer success", "solutions"],
                confidence=0.9,
                evidence=evidence,
            )
        if _has_any(text, ("engineering team", "software roles", "engineers", "technical team")):
            return HiringScopeResult(
                "engineering",
                role_categories=["software_engineer", "backend_engineer", "frontend_engineer", "full_stack_engineer", "infrastructure_engineer", "devops_engineer", "data_engineer", "ai_engineer", "ml_engineer"],
                department_terms=["engineering", "platform", "infrastructure", "security", "data", "ai", "ml"],
                team_terms=["engineering", "platform", "infrastructure", "devops", "sre", "security"],
                title_terms=["engineer", "backend", "frontend", "full stack", "infrastructure", "platform", "devops", "sre", "security", "data engineer", "ai engineer", "ml engineer"],
                confidence=0.88,
                evidence=evidence,
            )
        if _has_any(text, ("open roles", "join our team", "company is hiring", "is hiring", "several positions", "multiple roles")):
            return HiringScopeResult(
                "all_roles",
                confidence=0.82,
                broad_hiring=True,
                evidence=evidence,
                reason="broad_hiring_detected",
            )
        return HiringScopeResult("unknown", confidence=0.2, evidence=evidence, reason="scope_unknown")


def _specific_role(normalized_title: str, text: str) -> bool:
    if normalized_title in {"open roles", "hiring", "is hiring", "gtm team", "engineering team", "join our team"}:
        return False
    role_words = (
        "engineer",
        "designer",
        "account executive",
        "marketing lead",
        "product manager",
        "developer advocate",
        "recruiter",
    )
    return any(word in normalized_title for word in role_words) and not re.search(r"\b(team|roles|multiple)\b", normalized_title)


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _keywords(value: str | None) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9+#.]+", (value or "").lower()) if len(token) > 2][:12]


def _payload_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(str(item) for item in value.values() if isinstance(item, (str, int, float)))
    return str(value or "")


def _bounded(value: str, maximum: int = 1000) -> str:
    return value[:maximum]
