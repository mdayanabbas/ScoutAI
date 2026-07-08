from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class CandidateUrlType(StrEnum):
    FIRST_PARTY = "first_party"
    GITHUB_REPOSITORY = "github_repository"
    YC_COMPANY = "yc_company"
    YC_JOB = "yc_job"
    ASHBY_JOB = "ashby_job"
    GREENHOUSE_JOB = "greenhouse_job"
    LEVER_JOB = "lever_job"
    HACKER_NEWS = "hacker_news"
    YOUTUBE = "youtube"
    APP_STORE = "app_store"
    SOCIAL_PLATFORM = "social_platform"
    UNKNOWN_PLATFORM = "unknown_platform"
    MISSING = "missing"


@dataclass(frozen=True)
class CandidateUrlClassification:
    original_url: str | None
    url_type: CandidateUrlType
    platform: str | None = None
    first_party_url: str | None = None
    external_url: str | None = None
    external_company_slug: str | None = None
    external_repository: str | None = None
    is_first_party_company_domain: bool = False

    def model_dump(self) -> dict[str, str | bool | None]:
        return {
            "original_url": self.original_url,
            "url_type": self.url_type.value,
            "platform": self.platform,
            "first_party_url": self.first_party_url,
            "external_url": self.external_url,
            "external_company_slug": self.external_company_slug,
            "external_repository": self.external_repository,
            "is_first_party_company_domain": self.is_first_party_company_domain,
        }


def classify_candidate_url(url: str | None) -> CandidateUrlClassification:
    original_url = (url or "").strip() or None
    if original_url is None:
        return CandidateUrlClassification(None, CandidateUrlType.MISSING)

    parsed = urlparse(original_url if "://" in original_url else f"https://{original_url}")
    domain = (parsed.netloc or "").lower()
    if domain.startswith("www."):
        domain = domain[4:]
    path_parts = [part for part in parsed.path.split("/") if part]

    if domain == "github.com":
        if len(path_parts) >= 2:
            owner, repository = path_parts[0], path_parts[1]
            return _platform(
                original_url,
                CandidateUrlType.GITHUB_REPOSITORY,
                "github",
                external_repository=f"{owner}/{repository}",
            )
        return _platform(original_url, CandidateUrlType.UNKNOWN_PLATFORM, "github")

    if domain == "ycombinator.com" and len(path_parts) >= 2:
        if path_parts[0] == "companies":
            slug = path_parts[1]
            url_type = (
                CandidateUrlType.YC_JOB
                if len(path_parts) >= 3 and path_parts[2] == "jobs"
                else CandidateUrlType.YC_COMPANY
            )
            return _platform(original_url, url_type, "ycombinator", slug)
    if domain == "ycombinator.com":
        return _platform(original_url, CandidateUrlType.UNKNOWN_PLATFORM, "ycombinator")

    if domain == "jobs.ashbyhq.com" and path_parts:
        return _platform(original_url, CandidateUrlType.ASHBY_JOB, "ashby", path_parts[0])
    if domain.endswith("ashbyhq.com"):
        return _platform(original_url, CandidateUrlType.UNKNOWN_PLATFORM, "ashby")

    if domain == "boards.greenhouse.io" and path_parts:
        return _platform(
            original_url, CandidateUrlType.GREENHOUSE_JOB, "greenhouse", path_parts[0]
        )
    if domain.endswith("greenhouse.io"):
        return _platform(original_url, CandidateUrlType.UNKNOWN_PLATFORM, "greenhouse")

    if domain == "jobs.lever.co" and path_parts:
        return _platform(original_url, CandidateUrlType.LEVER_JOB, "lever", path_parts[0])
    if domain.endswith("lever.co"):
        return _platform(original_url, CandidateUrlType.UNKNOWN_PLATFORM, "lever")

    if domain in {"news.ycombinator.com", "hn.algolia.com"}:
        return _platform(original_url, CandidateUrlType.HACKER_NEWS, "hacker_news")

    if domain in {"youtube.com", "youtu.be"} or domain.endswith(".youtube.com"):
        return _platform(original_url, CandidateUrlType.YOUTUBE, "youtube")

    if domain in {"apps.apple.com", "play.google.com"}:
        return _platform(original_url, CandidateUrlType.APP_STORE, "app_store")

    if domain in {"linkedin.com", "x.com", "twitter.com"} or domain.endswith(
        (".linkedin.com", ".twitter.com")
    ):
        platform = "x" if domain == "x.com" else domain.split(".")[-2]
        return _platform(original_url, CandidateUrlType.SOCIAL_PLATFORM, platform)

    if not domain or "." not in domain:
        return _platform(original_url, CandidateUrlType.UNKNOWN_PLATFORM, None)

    return CandidateUrlClassification(
        original_url=original_url,
        url_type=CandidateUrlType.FIRST_PARTY,
        first_party_url=original_url,
        is_first_party_company_domain=True,
    )


def build_candidate_identity(
    source: str,
    source_identifier: str,
    normalized_domain: str | None,
    raw_payload: dict | None,
) -> str:
    classification = (raw_payload or {}).get("url_classification") or {}
    url_type = classification.get("url_type")
    platform = classification.get("platform")
    slug = classification.get("external_company_slug")
    repository = classification.get("external_repository")

    if url_type == CandidateUrlType.FIRST_PARTY.value and normalized_domain:
        return f"domain:{normalized_domain}"
    if platform == "github" and repository:
        return f"github:{repository.lower()}"
    if platform == "ycombinator" and slug:
        return f"yc:{slug.lower()}"
    if platform in {"ashby", "greenhouse", "lever"} and slug:
        return f"{platform}:{slug.lower()}"
    if normalized_domain and not platform:
        return f"domain:{normalized_domain}"
    return f"source:{source}:{source_identifier}"


def _platform(
    original_url: str,
    url_type: CandidateUrlType,
    platform: str | None,
    external_company_slug: str | None = None,
    external_repository: str | None = None,
) -> CandidateUrlClassification:
    return CandidateUrlClassification(
        original_url=original_url,
        url_type=url_type,
        platform=platform,
        external_url=original_url,
        external_company_slug=external_company_slug,
        external_repository=external_repository,
        is_first_party_company_domain=False,
    )
