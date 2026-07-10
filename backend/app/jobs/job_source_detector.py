import ipaddress
import logging
import posixpath
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse

from app.enrichment.domain_extractor import is_valid_hostname
from app.jobs.source_detection import JobSourceDetectionResult
from app.utils.enums import JobSourceType
from app.utils.urls import normalize_domain

logger = logging.getLogger(__name__)

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "gh_src",
}
UNSUPPORTED_SCHEMES = {"javascript", "data", "file", "ftp", "mailto"}
PLACEHOLDER_DOMAINS = {"example.invalid", "invalid.example", "placeholder.com"}
YC_JOB_RE = re.compile(r"^[A-Za-z0-9]+")
ASHBY_SAFE_PART_RE = re.compile(r"^[A-Za-z0-9_-]{1,120}$")
PUBLIC_SUFFIX_SECOND_LEVELS = {"co", "com", "net", "org", "ac", "gov"}


@dataclass(frozen=True)
class NormalizedJobURL:
    original_url: str
    normalized_url: str | None = None
    canonical_url: str | None = None
    normalized_domain: str | None = None
    path: str | None = None
    reason: str = "valid_supported_source"
    valid: bool = False
    evidence: dict[str, str | bool | list[str]] | None = None


@dataclass(frozen=True)
class YCJobURL:
    company_slug: str
    job_path: str
    job_identifier: str
    canonical_url: str


@dataclass(frozen=True)
class AshbyJobURL:
    board_slug: str
    job_identifier: str | None
    canonical_url: str
    board_level: bool
    exact_posting: bool


class JobSourceDetector:
    def detect(
        self,
        job_url: str | None,
        *,
        company_domain: str | None = None,
        source_platform: str | None = None,
    ) -> JobSourceDetectionResult:
        normalized = normalize_job_url(job_url)
        if not normalized.valid:
            logger.info(
                "Invalid job URL rejected",
                extra={"reason": normalized.reason, "source_platform": source_platform},
            )
            return JobSourceDetectionResult(
                source_type=JobSourceType.INVALID,
                original_url=(job_url or "").strip() or None,
                reason=normalized.reason,
                evidence=normalized.evidence or {},
            )
        logger.info(
            "Job URL normalized",
            extra={
                "normalized_domain": normalized.normalized_domain,
                "path": normalized.path,
                "stripped_query_params": (normalized.evidence or {}).get(
                    "stripped_query_params", []
                ),
            },
        )

        yc = parse_yc_job_url(normalized.canonical_url)
        if yc:
            logger.info(
                "YC job parsed",
                extra={"company_slug": yc.company_slug, "job_identifier": yc.job_identifier},
            )
            return JobSourceDetectionResult(
                source_type=JobSourceType.YCOMBINATOR_JOB,
                original_url=normalized.original_url,
                normalized_url=normalized.normalized_url,
                canonical_url=yc.canonical_url,
                normalized_domain=normalized.normalized_domain,
                provider="ycombinator",
                company_slug=yc.company_slug,
                job_identifier=yc.job_identifier,
                path=normalized.path,
                supported=True,
                confidence=1.0,
                reason="valid_supported_source",
                evidence={"parser": "yc_job_url"},
            )

        ashby = parse_ashby_job_url(normalized.canonical_url)
        if ashby:
            logger.info(
                "Ashby posting parsed" if ashby.exact_posting else "Ashby board parsed",
                extra={"board_slug": ashby.board_slug, "exact_posting": ashby.exact_posting},
            )
            return JobSourceDetectionResult(
                source_type=JobSourceType.ASHBY_JOB_BOARD,
                original_url=normalized.original_url,
                normalized_url=normalized.normalized_url,
                canonical_url=ashby.canonical_url,
                normalized_domain=normalized.normalized_domain,
                provider="ashby",
                job_identifier=ashby.job_identifier,
                board_slug=ashby.board_slug,
                path=normalized.path,
                supported=True,
                confidence=0.98 if ashby.exact_posting else 0.9,
                reason=(
                    "valid_supported_source"
                    if ashby.exact_posting
                    else "ashby_board_requires_job_matching"
                ),
                evidence={
                    "board_level": ashby.board_level,
                    "exact_posting": ashby.exact_posting,
                },
            )

        if company_domain and compare_registrable_domains(
            normalized.normalized_domain, company_domain
        ):
            logger.info(
                "First-party job page detected",
                extra={"normalized_domain": normalized.normalized_domain},
            )
            return JobSourceDetectionResult(
                source_type=JobSourceType.FIRST_PARTY_JOB_PAGE,
                original_url=normalized.original_url,
                normalized_url=normalized.normalized_url,
                canonical_url=normalized.canonical_url,
                normalized_domain=normalized.normalized_domain,
                provider="first_party",
                path=normalized.path,
                is_first_party=True,
                supported=True,
                confidence=0.95,
                reason="valid_supported_source",
                evidence={"company_domain": company_domain},
            )

        logger.info(
            "Unsupported job source detected",
            extra={"normalized_domain": normalized.normalized_domain},
        )
        return JobSourceDetectionResult(
            source_type=JobSourceType.GENERIC_EXTERNAL_JOB_PAGE,
            original_url=normalized.original_url,
            normalized_url=normalized.normalized_url,
            canonical_url=normalized.canonical_url,
            normalized_domain=normalized.normalized_domain,
            path=normalized.path,
            is_first_party=False,
            supported=False,
            confidence=0.6,
            reason="unsupported_job_source",
            evidence={"source_platform": source_platform} if source_platform else {},
        )


def normalize_job_url(value: str | None) -> NormalizedJobURL:
    original = (value or "").strip()
    if not original:
        return NormalizedJobURL(original, reason="missing_job_url", evidence={})
    if _explicit_unsupported_scheme(original):
        return NormalizedJobURL(original, reason="unsupported_scheme", evidence={})

    candidate = original if "://" in original else f"https://{original}"
    try:
        parsed = urlparse(candidate)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return NormalizedJobURL(original, reason="malformed_job_url", evidence={})

    if parsed.scheme not in {"http", "https"}:
        return NormalizedJobURL(original, reason="unsupported_scheme", evidence={})
    if parsed.username or parsed.password:
        return NormalizedJobURL(original, reason="embedded_credentials", evidence={})
    if not host:
        return NormalizedJobURL(original, reason="malformed_job_url", evidence={})

    normalized_host = _normalize_host(host)
    if not normalized_host or _unsafe_host(normalized_host):
        return NormalizedJobURL(original, reason="unsafe_host", evidence={})
    if normalized_host in PLACEHOLDER_DOMAINS:
        return NormalizedJobURL(original, reason="unsafe_host", evidence={})
    if not _is_ip_host(normalized_host) and not is_valid_hostname(normalized_host):
        return NormalizedJobURL(original, reason="malformed_job_url", evidence={})

    path = _normalize_path(parsed.path)
    query, stripped = _normalize_query(parsed.query)
    netloc = normalized_host
    if port and not (
        (parsed.scheme == "http" and port == 80)
        or (parsed.scheme == "https" and port == 443)
    ):
        netloc = f"{normalized_host}:{port}"
    canonical = urlunparse(("https", netloc, path, "", query, ""))
    return NormalizedJobURL(
        original_url=original,
        normalized_url=canonical,
        canonical_url=canonical,
        normalized_domain=normalize_domain(normalized_host),
        path=path,
        valid=True,
        reason="valid_supported_source",
        evidence={"stripped_query_params": stripped},
    )


def parse_yc_job_url(value: str | None) -> YCJobURL | None:
    normalized = normalize_job_url(value)
    if not normalized.valid or normalized.normalized_domain != "ycombinator.com":
        return None
    parsed = urlparse(normalized.canonical_url or "")
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) != 4 or parts[0] != "companies" or parts[2] != "jobs":
        return None
    company_slug = parts[1]
    job_path = parts[3]
    if not re.fullmatch(r"[a-z0-9-]{1,80}", company_slug):
        return None
    match = YC_JOB_RE.match(job_path)
    if not match:
        return None
    canonical = f"https://www.ycombinator.com/companies/{company_slug}/jobs/{quote(job_path, safe='-._~')}"
    return YCJobURL(company_slug, job_path, match.group(0), canonical)


def parse_ashby_job_url(value: str | None) -> AshbyJobURL | None:
    normalized = normalize_job_url(value)
    if not normalized.valid or normalized.normalized_domain != "jobs.ashbyhq.com":
        return None
    parsed = urlparse(normalized.canonical_url or "")
    parts = [unquote(part) for part in parsed.path.split("/") if part]
    if len(parts) not in {1, 2}:
        return None
    if not all(ASHBY_SAFE_PART_RE.fullmatch(part) for part in parts):
        return None
    board_slug = parts[0]
    if len(parts) == 1:
        return AshbyJobURL(
            board_slug=board_slug,
            job_identifier=None,
            canonical_url=f"https://jobs.ashbyhq.com/{quote(board_slug, safe='-._~')}",
            board_level=True,
            exact_posting=False,
        )
    posting_id = parts[1]
    return AshbyJobURL(
        board_slug=board_slug,
        job_identifier=posting_id,
        canonical_url=(
            f"https://jobs.ashbyhq.com/{quote(board_slug, safe='-._~')}/"
            f"{quote(posting_id, safe='-._~')}"
        ),
        board_level=False,
        exact_posting=True,
    )


def compare_registrable_domains(left: str | None, right: str | None) -> bool:
    return bool(left and right and _registrable_domain(left) == _registrable_domain(right))


def _normalize_host(host: str) -> str:
    value = host.strip().lower().rstrip(".")
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return ""
    if value.startswith("www."):
        value = value[4:]
    return value


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    collapsed = re.sub(r"/+", "/", path)
    normalized = posixpath.normpath(collapsed)
    if normalized in {".", "/"}:
        return ""
    if collapsed.endswith("/") and normalized != "/":
        normalized = normalized.rstrip("/")
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return quote(unquote(normalized), safe="/-._~")


def _normalize_query(query: str) -> tuple[str, list[str]]:
    pairs = parse_qsl(query, keep_blank_values=True)
    kept: list[tuple[str, str]] = []
    stripped: list[str] = []
    for key, value in pairs:
        if key.lower() in TRACKING_PARAMS:
            stripped.append(key)
            continue
        kept.append((key, value))
    return urlencode(kept, doseq=True), stripped


def _explicit_unsupported_scheme(value: str) -> bool:
    prefix = value.split(":", 1)[0].lower()
    return ":" in value and prefix in UNSUPPORTED_SCHEMES


def _unsafe_host(host: str) -> bool:
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _is_ip_host(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _registrable_domain(value: str) -> str:
    domain = normalize_domain(value).lower().rstrip(".")
    labels = domain.split(".")
    if len(labels) <= 2:
        return domain
    if labels[-2] in PUBLIC_SUFFIX_SECOND_LEVELS and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])
