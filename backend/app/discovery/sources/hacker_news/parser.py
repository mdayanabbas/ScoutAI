import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.discovery.sources.hacker_news.schemas import (
    HackerNewsDiscoveryRequest,
    HackerNewsItem,
)
from app.schemas.discovery import DiscoveryEvidenceInput

MAX_EXCERPT_LENGTH = 500
MAX_CANDIDATE_NAME_LENGTH = 80
HN_DOMAINS = {"news.ycombinator.com", "hn.algolia.com", "hacker-news.firebaseio.com"}
JOB_BOARD_DOMAINS = {
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "bamboohr.com",
    "job-boards.greenhouse.io",
}


def clean_hacker_news_html(value: str | None) -> str | None:
    if value is None:
        return None
    soup = BeautifulSoup(value, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r" *\n *", "\n", text).strip()
    return text or None


def extract_candidate_name(item: HackerNewsItem) -> str | None:
    title = (item.title or "").strip()
    if not title:
        return None
    if title.lower().startswith("show hn:"):
        return _clean_candidate_name(
            re.split(
                r"\s+(?:[-\u2013\u2014]|\u00e2\u20ac\u201c|\u00e2\u20ac\u201d|\|)\s+|,|\s+-\s+",
                title[8:],
                maxsplit=1,
            )[0]
        )
    return _extract_job_candidate_name(title)


def extract_candidate_website(item: HackerNewsItem) -> str | None:
    if not item.url:
        return None
    parsed = urlparse(item.url)
    domain = (parsed.netloc or "").lower()
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain or domain in HN_DOMAINS:
        return None
    if any(domain == job_domain or domain.endswith(f".{job_domain}") for job_domain in JOB_BOARD_DOMAINS):
        return None
    return item.url


def build_candidate_description(item: HackerNewsItem) -> str | None:
    cleaned_text = clean_hacker_news_html(item.text)
    if cleaned_text:
        return cleaned_text
    return (item.title or "").strip() or None


def build_hacker_news_evidence(item: HackerNewsItem, feed: str | None = None) -> DiscoveryEvidenceInput:
    description = build_candidate_description(item)
    excerpt = _truncate_excerpt(description or item.title or "")
    published_at = (
        datetime.fromtimestamp(item.time, timezone.utc) if item.time is not None else None
    )
    return DiscoveryEvidenceInput(
        evidence_type="launch_post" if feed == "show" else "hiring_post",
        source_url=f"https://news.ycombinator.com/item?id={item.id}",
        title=item.title,
        excerpt=excerpt,
        published_at=published_at,
        metadata={
            "hacker_news_item_id": item.id,
            "author": item.by,
            "score": item.score,
            "descendants": item.descendants,
            "item_type": item.type,
            "feed": feed,
        },
    )


def is_candidate_item(item: HackerNewsItem, request: HackerNewsDiscoveryRequest) -> bool:
    if item.deleted or item.dead:
        return False
    if item.type not in {"story", "job"} or not item.title:
        return False
    if request.minimum_score is not None and (item.score or 0) < request.minimum_score:
        return False
    if extract_candidate_name(item) is None:
        return False
    if not request.include_items_without_website and extract_candidate_website(item) is None:
        return False
    return True


def _extract_job_candidate_name(title: str) -> str | None:
    patterns = [
        r"^(?P<company>.+?)\s+\([^)]*\)\s+is hiring\b",
        r"^(?P<company>.+?)\s+is hiring\b",
        r"^(?P<company>.+?)\s+hiring\b",
        r"^(?P<company>.+?)\s+wants to hire\b",
        r"^(?P<company>.+?)\s+is looking for\b",
        r"\bat\s+(?P<company>[A-Z][A-Za-z0-9 .&'-]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return _clean_candidate_name(match.group("company"))
    return None


def _clean_candidate_name(value: str | None) -> str | None:
    if value is None:
        return None
    name = re.sub(r"\s+", " ", value).strip(" \t\n\r-:|,.;()[]{}")
    if not name or len(name) > MAX_CANDIDATE_NAME_LENGTH:
        return None
    if len(name.split()) > 8:
        return None
    return name


def _truncate_excerpt(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if len(cleaned) <= MAX_EXCERPT_LENGTH:
        return cleaned
    return cleaned[: MAX_EXCERPT_LENGTH - 3].rstrip() + "..."
