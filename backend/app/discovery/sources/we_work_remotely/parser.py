import xml.etree.ElementTree as ET
from typing import Any

from app.discovery.sources.we_work_remotely.models import (
    WWRFeedDefinition,
    WWRFeedItem,
    WWRFeedMetadata,
    WWRFeedParseResult,
    WWRParseFailure,
)
from app.discovery.sources.we_work_remotely.normalizer import (
    canonical_wwr_url,
    clean_html_text,
    normalize_employment_type,
    parse_rss_datetime,
    parse_salary,
    parse_title_parts,
)

MAX_XML_BYTES = 5_000_000
MAX_DEPTH = 32


class WeWorkRemotelyRSSParser:
    def parse(self, body: bytes, *, feed: WWRFeedDefinition) -> WWRFeedParseResult:
        warnings: list[str] = []
        if len(body) > MAX_XML_BYTES:
            return WWRFeedParseResult(WWRFeedMetadata(), warnings=["wwr_xml_too_large"])
        sample = body[:500].lower()
        if b"<!doctype" in sample or b"<!entity" in sample:
            return WWRFeedParseResult(WWRFeedMetadata(), warnings=["wwr_unsafe_xml"])
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return WWRFeedParseResult(WWRFeedMetadata(), warnings=["wwr_invalid_xml"])
        if _too_deep(root):
            return WWRFeedParseResult(WWRFeedMetadata(), warnings=["wwr_xml_too_deep"])
        channel = root.find("channel")
        if channel is None:
            channel = root
        metadata = WWRFeedMetadata(
            title=_child_text(channel, "title"),
            link=_child_text(channel, "link"),
            description=_child_text(channel, "description"),
            last_build_date=parse_rss_datetime(_child_text(channel, "lastBuildDate"))[0],
            language=_child_text(channel, "language"),
        )
        items: list[WWRFeedItem] = []
        failures: list[WWRParseFailure] = []
        for index, item in enumerate(channel.findall("item")):
            try:
                parsed = _parse_item(item, index=index, feed=feed)
                if parsed.link is None:
                    failures.append(WWRParseFailure(index, parsed.guid, ["link"], "invalid_link"))
                    continue
                items.append(parsed)
            except Exception:
                failures.append(WWRParseFailure(index, _child_text(item, "guid"), ["item"], "malformed_item"))
        return WWRFeedParseResult(metadata, items=items, malformed_items=failures, warnings=warnings)


def _parse_item(item: ET.Element, *, index: int, feed: WWRFeedDefinition) -> WWRFeedItem:
    title = _child_text(item, "title")
    raw_html = _child_text(item, "encoded") or _child_text(item, "description")
    text = clean_html_text(raw_html)
    company, role = parse_title_parts(title, text)
    published_at, pub_warning = parse_rss_datetime(_child_text(item, "pubDate"))
    categories = _dedupe([_text(child) for child in item.findall("category")])
    region = _namespace_value(item, ("region", "location", "geo"))
    employment = _namespace_value(item, ("type", "job_type", "employmentType")) or _employment_from_text(text)
    salary_text = _namespace_value(item, ("salary", "compensation")) or parse_salary(text)[3]
    warnings = [pub_warning] if pub_warning else []
    return WWRFeedItem(
        guid=_child_text(item, "guid"),
        title=title,
        link=canonical_wwr_url(_child_text(item, "link")),
        published_at=published_at,
        description_html=raw_html,
        description_text=text,
        categories=categories,
        company_name=company,
        role_title=role,
        region_text=region,
        employment_type=normalize_employment_type(employment),
        salary_text=salary_text,
        source_feed=feed.feed_type,
        warnings=warnings,
    )


def _child_text(parent: ET.Element, name: str) -> str | None:
    for child in list(parent):
        if _local_name(child.tag) == name:
            return _text(child)
    return None


def _namespace_value(parent: ET.Element, names: tuple[str, ...]) -> str | None:
    wanted = {name.lower() for name in names}
    for child in list(parent):
        if _local_name(child.tag).lower() in wanted:
            return _text(child)
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _dedupe(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _too_deep(root: ET.Element) -> bool:
    stack = [(root, 1)]
    while stack:
        element, depth = stack.pop()
        if depth > MAX_DEPTH:
            return True
        stack.extend((child, depth + 1) for child in list(element))
    return False


def _employment_from_text(text: str | None) -> str | None:
    value = (text or "").lower()
    for label in ("full-time", "full time", "contractor", "contract", "part-time", "part time", "internship", "temporary", "freelance"):
        if label in value:
            return label
    return None
