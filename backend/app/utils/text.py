import re
from typing import Any

MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "â€",
    "â€“",
    "â€”",
    "â€™",
    "â€œ",
    "â€�",
    "â„¢",
    "ï¿½",
    "ðŸ",
    "Ã°",
)
MOJIBAKE_REPLACEMENTS = {
    "\u00c3\u0192\u00c2\u00a2\u00c3\u00a2\u20ac\u00c3\u00a2\u00e2\u201e\u00a2": "\u2019",
    "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢": "\u2019",
    "ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ": "\u201c",
    "ÃƒÂ¢Ã¢â€šÂ¬Ã¯Â¿Â½": "\u201d",
    "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“": "\u2013",
    "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â�": "\u2014",
    "ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢": "\u2019",
    "ÃƒÂ¢Ã¢€Ã¢â„¢": "\u2019",
    "ÃƒÂ¢Ã¢€Ã¢â„¢": "\u2019",
    "ÃƒÂ¢Ã¢€Ã…â€œ": "\u201c",
    "ÃƒÂ¢Ã¢€Ã¯Â¿Â½": "\u201d",
    "ÃƒÂ¢Ã¢€Ã¢â‚¬Å“": "\u2013",
    "Ã¢â‚¬â„¢": "\u2019",
    "Ã¢â‚¬Å“": "\u201c",
    "Ã¢â‚¬ï¿½": "\u201d",
    "Ã¢â‚¬Â�": "\u201d",
    "Ã¢â‚¬â€œ": "\u2013",
    "Ã¢â‚¬â€": "\u2014",
    "Ã¢â€šÂ¬": "\u20ac",
    "â€™": "\u2019",
    "â€œ": "\u201c",
    "â€�": "\u201d",
    "â€“": "\u2013",
    "â€”": "\u2014",
    "â‚¬": "\u20ac",
}
ACTION_SUFFIX_RE = re.compile(
    r"\s+(?:apply(?:\s+now)?|view\s+(?:role|position|job)|learn\s+more|details|read\s+more)\s*$",
    re.IGNORECASE,
)
TITLE_ABBREVIATIONS = {
    "swe": "software engineer",
    "sde": "software development engineer",
    "fde": "forward deployed engineer",
}
GENERIC_SKILL_HEADINGS = {
    "about you",
    "bonus",
    "bonus points",
    "nice to have",
    "preferred qualifications",
    "requirements",
    "skills",
    "technologies",
    "what you'll do",
    "you have",
}


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    repaired = repair_mojibake(value) or ""
    normalized = re.sub(r"\s+", " ", repaired.strip())
    return normalized or None


def normalize_title(value: str | None) -> str | None:
    normalized = normalize_text(value)
    return normalized.lower() if normalized is not None else None


def repair_mojibake(text: str | None, *, max_chars: int = 200_000) -> str | None:
    if text is None:
        return None
    value = str(text)
    if not value or not _has_mojibake_marker(value):
        return value
    bounded = value[:max_chars]
    best = _replace_known_mojibake(bounded)
    best_score = _mojibake_score(best)
    for _ in range(5):
        candidate = _decode_mojibake_once(best)
        if candidate is None or candidate == best:
            break
        candidate = _replace_known_mojibake(candidate)
        candidate_score = _mojibake_score(candidate)
        if candidate_score > best_score:
            break
        best = candidate
        best_score = candidate_score
    if len(value) > max_chars:
        best += value[max_chars:]
    return best


def clean_text_value(value: Any) -> str | None:
    return normalize_text(str(value)) if value is not None else None


def clean_text_list(values: list[Any] | None) -> list[str] | None:
    if not values:
        return None
    cleaned = dedupe_meaningful_entries(values)
    return cleaned or None


def strip_job_title_action_suffix(title: str | None) -> str | None:
    value = normalize_text(title)
    if not value:
        return None
    previous = value
    while True:
        cleaned = ACTION_SUFFIX_RE.sub("", previous).strip()
        if cleaned == previous:
            return cleaned
        previous = cleaned


def should_replace_job_title(
    existing_title: str | None,
    extracted_title: str | None,
    extracted_confidence: float | None,
    extracted_source: str | None,
) -> bool:
    existing = strip_job_title_action_suffix(existing_title)
    extracted = strip_job_title_action_suffix(extracted_title)
    if not existing or not extracted:
        return bool(extracted and (extracted_confidence or 0) >= 0.9)
    if (extracted_confidence or 0) < 0.9 or extracted_source == "url_slug":
        return False
    existing_key = _title_key(existing)
    extracted_key = _title_key(extracted)
    if existing_key == extracted_key:
        return existing != extracted
    if existing_key in TITLE_ABBREVIATIONS and TITLE_ABBREVIATIONS[existing_key] in extracted_key:
        return True
    if existing_key == "devrel" and (
        "developer relations" in extracted_key or "developer advocate" in extracted_key
    ):
        return True
    if _generic_or_sentence_title(existing):
        return True
    if len(existing_key) >= 8 and extracted_key.startswith(existing_key) and len(extracted_key) > len(existing_key) + 4:
        return True
    if _word_subset(existing_key, extracted_key) and len(extracted_key) > len(existing_key) + 4:
        return True
    return False


def dedupe_meaningful_entries(items: list[Any], *, maximum: int = 30, max_length: int = 120) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = normalize_text(str(item)) or ""
        cleaned = cleaned.strip(" -*•.;:")
        if not _meaningful_entry(cleaned, max_length=max_length):
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= maximum:
            break
    return result


def split_structured_skill_text(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = repair_mojibake(str(value)) or ""
    lines = [line.strip(" -*•\t") for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines
    return [
        item.strip()
        for item in re.split(r"[,;|•]", text)
        if item.strip()
    ]


def focused_authorization_fields(
    labels: dict[str, str],
    text: str,
) -> tuple[str | None, str | None]:
    labelled = []
    for key in ("visa", "sponsorship", "work_authorization"):
        if labels.get(key):
            labelled.append(labels[key])
    candidates = labelled or _authorization_sentences(text)
    if not candidates:
        return None, None
    focused = _bounded_join(dedupe_meaningful_entries(candidates, maximum=4, max_length=500), 500)
    lower = focused.lower() if focused else ""
    if not focused:
        return None, None
    visa = None
    immigration = re.search(r"\b(visa|immigration|work authorization|authorized to work|right to work|sponsorship)\b", lower)
    clearance_only = (
        re.search(r"\b(clearance|ts/sci|polygraph)\b", lower)
        and not re.search(r"\b(visa|immigration|work authorization|authorized to work|right to work|u\.?s\.? citizen|us citizen)\b", lower)
    )
    if re.search(r"\b(unable to sponsor|no visa sponsorship|does not sponsor|cannot sponsor)\b", lower):
        visa = "does_not_sponsor"
    elif re.search(r"\b(visa sponsorship available|will sponsor visas?|immigration sponsorship|sponsor work visas?)\b", lower):
        visa = "sponsors"
    elif re.search(r"\b(u\.?s\.? citizen|u\.?s\.? citizenship|us citizen|us citizenship|citizen only|must be a .*citizen)\b", lower):
        visa = "restricted"
    elif immigration and not clearance_only:
        visa = "existing_authorization_required"
    return visa, focused


def _decode_mojibake_once(value: str) -> str | None:
    for encoding in ("cp1252", "latin-1"):
        try:
            return value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return None


def _replace_known_mojibake(value: str) -> str:
    repaired = value
    for corrupted, correct in MOJIBAKE_REPLACEMENTS.items():
        repaired = repaired.replace(corrupted, correct)
    return repaired


def _has_mojibake_marker(value: str) -> bool:
    return any(marker in value for marker in MOJIBAKE_MARKERS)


def _mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in MOJIBAKE_MARKERS) + _replacement_count(value) * 2


def _replacement_count(value: str) -> int:
    return value.count("\ufffd") + value.count("ï¿½")


def _title_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (normalize_text(value) or "").lower()).strip()


def _generic_or_sentence_title(value: str) -> bool:
    key = _title_key(value)
    return key in {"careers", "hiring", "jobs", "open roles", "largest government contract"} or " is hiring" in key


def _word_subset(existing_key: str, extracted_key: str) -> bool:
    existing_words = set(existing_key.split())
    extracted_words = set(extracted_key.split())
    return bool(existing_words) and existing_words < extracted_words


def _meaningful_entry(value: str, *, max_length: int) -> bool:
    if not value or len(value) > max_length:
        return False
    key = value.casefold()
    if key in GENERIC_SKILL_HEADINGS:
        return False
    alnum = re.sub(r"[^A-Za-z0-9+#]", "", value)
    if len(alnum) < 2:
        return False
    if key in {"co", "hands", "on", "with", "and", "or", "the", "marketing"}:
        return False
    return True


def _authorization_sentences(text: str) -> list[str]:
    cleaned = repair_mojibake(text) or ""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
    strong = re.compile(
        r"authorized to work|work authorization|visa sponsorship|sponsorship|must be a\s+u\.?s\.?\s+citizen|us citizen only|existing authorization|required right to work|right to work|security clearance|(?:citizenship|eligible|eligibility|required|clearance).{0,80}ts/sci|ts/sci.{0,80}(?:citizenship|eligible|eligibility|required|clearance)",
        re.IGNORECASE,
    )
    return [normalize_text(sentence) or "" for sentence in sentences if strong.search(sentence)]


def _bounded_join(items: list[str], maximum: int) -> str | None:
    result = " ".join(items)
    return result[:maximum].rstrip() or None
