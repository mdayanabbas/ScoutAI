import re
from typing import Any
from uuid import UUID

from app.core.errors import ValidationAppError
from app.utils.enums import CompanyStage, RemoteType, RoleCategory

MAX_TARGET_TITLES = 50
MAX_ROLE_CATEGORIES = 50
MAX_SENIORITY = 20
MAX_SKILLS = 200
MAX_TECHNOLOGIES = 200
MAX_LOCATIONS = 100
MAX_COUNTRIES = 100
MAX_COMPANY_STAGES = 20
MAX_COMPANY_SIZES = 20
MAX_EXCLUDED_TITLES = 100
MAX_EXCLUDED_COMPANIES = 500
MAX_NOTES_CHARS = 5000

PROFICIENCIES = ("beginner", "intermediate", "advanced", "expert")
PROFICIENCY_RANK = {value: index for index, value in enumerate(PROFICIENCIES)}
SENIORITY_VALUES = {
    "internship",
    "entry_level",
    "junior",
    "mid_level",
    "senior",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "executive",
    "open",
}
EMPLOYMENT_TYPES = {
    "full_time",
    "part_time",
    "contract",
    "internship",
    "temporary",
    "cofounder",
    "other",
}
COMPANY_SIZES = {
    "1_10",
    "11_50",
    "51_200",
    "201_500",
    "501_1000",
    "1001_plus",
    "unknown",
}
COMPANY_STAGES = {item.value for item in CompanyStage} | {"series_c_plus", "bootstrapped"}
ROLE_ALIASES = {"machine_learning_engineer": RoleCategory.ML_ENGINEER.value}
REMOTE_ALIASES = {
    "remote": RemoteType.REMOTE_WORLDWIDE.value,
    "onsite": RemoteType.ONSITE.value,
    "on_site": RemoteType.ONSITE.value,
    "hybrid": RemoteType.HYBRID.value,
    "unknown": RemoteType.UNKNOWN.value,
}
TITLE_ACRONYMS = {"ai", "ml", "nlp", "sre", "qa", "ui", "ux", "api"}
TITLE_SPECIAL = {"devops": "DevOps"}


def normalize_target_title(value: str) -> str:
    text = _collapse(value)
    if not text:
        raise ValidationAppError("Blank values are not allowed")
    words = re.split(r"(\s+|-)", text.lower())
    return "".join(_title_word(part) for part in words)


def normalize_role_category(value: str) -> str:
    normalized = _collapse(value).lower().replace("-", "_").replace(" ", "_")
    normalized = ROLE_ALIASES.get(normalized, normalized)
    allowed = {item.value for item in RoleCategory}
    if normalized not in allowed:
        raise ValidationAppError("Unsupported role category", {"role_category": value})
    return normalized


def normalize_seniority(value: str) -> str:
    normalized = _collapse(value).lower().replace("-", "_").replace(" ", "_")
    if normalized not in SENIORITY_VALUES:
        raise ValidationAppError("Unsupported seniority", {"seniority": value})
    return normalized


def normalize_remote_type(value: str) -> str:
    normalized = _collapse(value).lower().replace("-", "_").replace(" ", "_")
    normalized = REMOTE_ALIASES.get(normalized, normalized)
    allowed = {item.value for item in RemoteType}
    if normalized not in allowed:
        raise ValidationAppError("Unsupported remote type", {"remote_type": value})
    return normalized


def normalize_employment_type(value: str) -> str:
    normalized = _collapse(value).lower().replace("-", "_").replace(" ", "_")
    if normalized not in EMPLOYMENT_TYPES:
        raise ValidationAppError("Unsupported employment type", {"employment_type": value})
    return normalized


def normalize_country(value: str) -> str:
    return _title_preserve_acronyms(value)


def normalize_location(value: str) -> str:
    return _title_preserve_acronyms(value)


def normalize_skill_name(value: str) -> str:
    return _canonical_named(value)


def normalize_technology_name(value: str) -> str:
    return _canonical_named(value)


def normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    text = _collapse(value).upper()
    if not text:
        return None
    if len(text) > 8:
        raise ValidationAppError("salary_currency must be at most 8 characters")
    return text


def normalize_company_stage(value: str) -> str:
    normalized = _collapse(value).lower().replace("-", "_").replace(" ", "_")
    if normalized not in COMPANY_STAGES:
        raise ValidationAppError("Unsupported company stage", {"company_stage": value})
    return normalized


def normalize_company_size(value: str) -> str:
    normalized = _collapse(value).lower().replace("-", "_").replace(" ", "_").replace("+", "_plus")
    if normalized not in COMPANY_SIZES:
        raise ValidationAppError("Unsupported company size", {"company_size": value})
    return normalized


def normalize_company_id(value: str) -> str:
    text = _collapse(value)
    try:
        UUID(text)
    except ValueError as exc:
        raise ValidationAppError("Invalid company ID", {"company_id": value}) from exc
    return text


def normalize_profile_list(
    values: list[Any] | None,
    normalizer,
    *,
    maximum: int,
    field_name: str,
) -> list[Any]:
    if not values:
        return []
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalizer(str(value))
        key = str(normalized).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
        if len(result) > maximum:
            raise ValidationAppError(f"{field_name} exceeds maximum", {field_name: f"maximum {maximum}"})
    return result


def normalize_skill_entries(
    values: list[dict[str, Any]] | None,
    *,
    maximum: int,
    field_name: str,
    name_normalizer=normalize_skill_name,
) -> list[dict[str, Any]]:
    if not values:
        return []
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in values:
        name = name_normalizer(str(item.get("name", "")))
        key = name.lower()
        proficiency = item.get("proficiency")
        if proficiency is not None:
            proficiency = _collapse(str(proficiency)).lower()
            if proficiency not in PROFICIENCY_RANK:
                raise ValidationAppError("Unsupported proficiency", {"proficiency": proficiency})
        years = item.get("years_experience")
        if years is not None:
            years = float(years)
            if years < 0:
                raise ValidationAppError("years_experience cannot be negative")
        if key not in merged:
            order.append(key)
            merged[key] = {"name": name}
        current = merged[key]
        if proficiency is not None:
            existing = current.get("proficiency")
            if existing is None or PROFICIENCY_RANK[proficiency] > PROFICIENCY_RANK[existing]:
                current["proficiency"] = proficiency
        if years is not None:
            current["years_experience"] = max(float(current.get("years_experience", 0)), years)
    if len(order) > maximum:
        raise ValidationAppError(f"{field_name} exceeds maximum", {field_name: f"maximum {maximum}"})
    return [merged[key] for key in order]


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _title_word(value: str) -> str:
    if value.isspace() or value == "-":
        return value
    if value in TITLE_SPECIAL:
        return TITLE_SPECIAL[value]
    if value in TITLE_ACRONYMS:
        return value.upper()
    return value.capitalize()


def _title_preserve_acronyms(value: str) -> str:
    text = _collapse(value)
    if not text:
        raise ValidationAppError("Blank values are not allowed")
    return " ".join(_title_word(part.lower()) for part in text.split(" "))


def _canonical_named(value: str) -> str:
    text = _collapse(value)
    if not text:
        raise ValidationAppError("Blank values are not allowed")
    if len(text) > 100:
        raise ValidationAppError("name must be at most 100 characters")
    known = {
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "next.js": "Next.js",
        "node.js": "Node.js",
        "fastapi": "FastAPI",
        "sqlalchemy": "SQLAlchemy",
        "postgresql": "PostgreSQL",
        "langchain": "LangChain",
        "aws": "AWS",
        "gcp": "GCP",
        "api": "API",
        "ui": "UI",
        "ux": "UX",
        "c++": "C++",
        "c#": "C#",
    }
    return known.get(text.lower(), text[:1].upper() + text[1:])
