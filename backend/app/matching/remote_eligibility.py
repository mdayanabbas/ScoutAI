import re
from dataclasses import dataclass, field
from typing import Any


REMOTE_PRIORITY = {
    "work_from_anywhere": 0,
    "remote_india_eligible": 1,
    "remote_global_unspecified": 2,
    "remote_eligibility_unclear": 3,
    "remote_region_restricted": 4,
    "remote_country_restricted": 5,
    "hybrid": 6,
    "onsite": 7,
    "unknown": 8,
}


@dataclass(frozen=True)
class RemoteEligibilityResult:
    classification: str
    confidence: float
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)
    restrictions: list[str] = field(default_factory=list)
    reason: str = "unknown"


class RemoteEligibilityClassifier:
    def classify(self, job: Any, profile: Any | None = None) -> RemoteEligibilityResult:
        raw_remote_type = getattr(job, "remote_type", "") or ""
        remote_type = str(getattr(raw_remote_type, "value", raw_remote_type)).lower()
        text = _text(job)
        focused_sentences = _focused_sentences(job)
        location = str(getattr(job, "location", "") or "").lower()
        willing = getattr(profile, "willing_to_relocate", None)
        if remote_type == "onsite" or _has_onsite_requirement(focused_sentences):
            return _result("onsite", 0.95, negative=["onsite"], reason="onsite")
        if remote_type == "hybrid" or _has(text, r"\bhybrid\b"):
            return _result("hybrid", 0.95, negative=["hybrid"], reason="hybrid")
        if willing is False and _has_onsite_requirement(focused_sentences, relocation_only=True):
            return _result("onsite", 0.9, negative=["relocation_required"], reason="relocation_required")
        if _has_auth_restriction(text):
            return _result("remote_country_restricted", 0.95, negative=["authorization_restriction"], restrictions=["authorization"], reason="authorization_restriction")
        if _has(text, r"work from anywhere|remote worldwide|worldwide remote|globally remote|global remote|anywhere in the world|location independent|distributed worldwide|international remote|remote across all countries"):
            return _result("work_from_anywhere", 0.95, positive=["worldwide_remote"], reason="work_from_anywhere")
        if _has(text, r"india remote|remote in india|india-based|based anywhere in india|apac including india|international contractor|global contractor"):
            return _result("remote_india_eligible", 0.92, positive=["india_eligible"], reason="india_eligible")
        country_restriction = _country_restriction(text)
        if country_restriction:
            return _result("remote_country_restricted", 0.95, negative=[country_restriction], restrictions=[country_restriction], reason="country_restricted")
        region_restriction = _region_restriction(text)
        if region_restriction:
            return _result("remote_region_restricted", 0.85, negative=[region_restriction], restrictions=[region_restriction], reason="region_restricted")
        if remote_type in {"remote_worldwide"}:
            return _result("work_from_anywhere", 0.9, positive=["remote_worldwide"], reason="remote_worldwide")
        if remote_type in {"remote_country", "remote_region"}:
            return _result("remote_eligibility_unclear", 0.65, positive=[remote_type], restrictions=[location] if location else [], reason="remote_scope_missing")
        if "remote" in remote_type or _has_positive_remote_evidence(job, focused_sentences):
            return _result("remote_global_unspecified", 0.75, positive=["remote_signal"], reason="remote_no_restriction_found")
        return _result("unknown", 0.4, reason="missing_remote_data")


def _result(
    classification: str,
    confidence: float,
    *,
    positive: list[str] | None = None,
    negative: list[str] | None = None,
    restrictions: list[str] | None = None,
    reason: str,
) -> RemoteEligibilityResult:
    return RemoteEligibilityResult(classification, confidence, positive or [], negative or [], restrictions or [], reason)


def _text(job: Any) -> str:
    parts = [
        getattr(job, "location", None),
        getattr(job, "description", None),
        getattr(job, "work_authorization", None),
        getattr(job, "visa_sponsorship", None),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _focused_sentences(job: Any) -> list[str]:
    text = "\n".join(
        str(part or "")
        for part in (
            getattr(job, "description", None),
            getattr(job, "location", None),
        )
        if part
    )
    return [sentence.strip().lower() for sentence in re.split(r"(?<=[.!?])\s+|\n+", text) if sentence.strip()]


def _has_onsite_requirement(sentences: list[str], *, relocation_only: bool = False) -> bool:
    for sentence in sentences:
        if _optional_onsite_context(sentence):
            continue
        if relocation_only:
            if _has(sentence, r"\brelocation required\b|\bmust relocate\b|\brelocate to\b"):
                return True
            continue
        if _has(
            sentence,
            r"\bin person\b|\bin-person\b|\bon site\b|\bon-site\b|\bonsite\b|office based|office-based|work from our office|based in our office|must work from|must be based in|located in and working onsite|\brelocation required\b|\brelocate to\b|\bno remote\b|remote work is not available|this role is not remote|full time in person|full-time in person",
        ):
            return True
    return False


def _optional_onsite_context(sentence: str) -> bool:
    return _has(
        sentence,
        r"occasional company offsites?|optional office visits?|customer onsite visits?|annual team meetups?|team offsites?|company offsites?",
    )


def _has_positive_remote_evidence(job: Any, sentences: list[str]) -> bool:
    location = str(getattr(job, "location", "") or "").lower()
    if re.search(r"\bremote\b", location):
        return True
    for sentence in sentences:
        if _has(sentence, r"\bremote\b|work from anywhere|distributed team|location independent"):
            return True
    return False


def _has(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, re.IGNORECASE))


def _has_auth_restriction(text: str) -> bool:
    return _has(
        text,
        r"must be authorized to work in the united states|existing us work authorization|required us work authorization|us citizenship required|u\.s\. citizenship|required.*ts/sci|ts/sci.*required|security clearance required|existing eu work authorization|existing uk work authorization|no visa sponsorship",
    )


def _country_restriction(text: str) -> str | None:
    patterns = {
        "us_only": r"\bus only\b|united states only|must reside in the us|remote within the us|must be based in the (?:us|united states)",
        "canada_only": r"canada only|must reside in canada|remote within canada",
        "uk_only": r"\buk only\b|united kingdom only|must reside in the uk",
        "germany_only": r"germany only|must reside in germany",
    }
    for label, pattern in patterns.items():
        if _has(text, pattern):
            return label
    return None


def _region_restriction(text: str) -> str | None:
    patterns = {
        "eu_only": r"\beu only\b|\buk/eu\b|\beu timezone\b",
        "emea": r"\bemea\b",
        "americas": r"\bamericas\b|north america|us/canada",
        "timezone": r"\b(pst|est|cet|gmt) timezone\b",
    }
    for label, pattern in patterns.items():
        if _has(text, pattern):
            if label == "emea" and "india" in text:
                return None
            return label
    return None
