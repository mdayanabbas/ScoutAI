import re


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = re.sub(r"\s+", " ", value.strip())
    return normalized or None


def normalize_title(value: str | None) -> str | None:
    normalized = normalize_text(value)
    return normalized.lower() if normalized is not None else None
