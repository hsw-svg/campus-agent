"""Fetch and normalize public campus information from configured official sources."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Literal, cast
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx


Category = Literal["news", "activity", "notice"]
SourceFormat = Literal["rss", "html"]
MAX_RESPONSE_BYTES = 2_000_000
MAX_ITEMS_PER_SOURCE = 30
MAX_REDIRECTS = 3


class CampusNewsSourceError(ValueError):
    pass


@dataclass(frozen=True)
class CampusNewsSource:
    id: str
    category: Category
    source: str
    format: SourceFormat
    url: str
    allowed_domains: tuple[str, ...]
    item_selector: str | None = None
    title_selector: str | None = None
    date_selector: str | None = None
    link_selector: str | None = None
    summary_selector: str | None = None
    event_end_selector: str | None = None
    date_format: str | None = None


@dataclass(frozen=True)
class NormalizedCampusNewsItem:
    source_id: str
    category: Category
    title: str
    summary: str | None
    source: str
    url: str
    published_at: datetime
    event_end_at: datetime | None
    fingerprint: str


def parse_sources(raw: str) -> tuple[CampusNewsSource, ...]:
    if not raw.strip():
        return ()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CampusNewsSourceError("CAMPUS_NEWS_SOURCES_JSON is not valid JSON") from error
    if not isinstance(payload, list) or not payload:
        raise CampusNewsSourceError("campus news sources must be a non-empty JSON array")

    sources: list[CampusNewsSource] = []
    seen_ids: set[str] = set()
    for entry in payload:
        if not isinstance(entry, dict):
            raise CampusNewsSourceError("each campus news source must be an object")
        source_id = _required_text(entry, "id", 96)
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", source_id) or source_id in seen_ids:
            raise CampusNewsSourceError(f"invalid or duplicate source id: {source_id}")
        seen_ids.add(source_id)
        category = _required_text(entry, "category", 16)
        source_format = _required_text(entry, "format", 8)
        if category not in ("news", "activity", "notice"):
            raise CampusNewsSourceError(f"invalid category for source {source_id}")
        if source_format not in ("rss", "html"):
            raise CampusNewsSourceError(f"invalid format for source {source_id}")
        domains = entry.get("allowed_domains")
        if not isinstance(domains, list) or not domains:
            raise CampusNewsSourceError(f"allowed_domains is required for source {source_id}")
        allowed_domains = tuple(_normalize_domain(value) for value in domains)
        url = validate_official_url(_required_text(entry, "url", 1000), allowed_domains)
        selectors = {name: _optional_text(entry, name, 300) for name in (
            "item_selector", "title_selector", "date_selector", "link_selector",
            "summary_selector", "event_end_selector", "date_format",
        )}
        if source_format == "html" and not all(selectors[name] for name in ("item_selector", "title_selector", "date_selector", "link_selector")):
            raise CampusNewsSourceError(f"HTML selectors are incomplete for source {source_id}")
        sources.append(CampusNewsSource(
            id=source_id,
            category=cast(Category, category),
            source=_required_text(entry, "source", 160),
            format=cast(SourceFormat, source_format),
            url=url,
            allowed_domains=allowed_domains,
            **selectors,
        ))
    return tuple(sources)


def validate_official_url(value: str, allowed_domains: tuple[str, ...]) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise CampusNewsSourceError("only credential-free HTTP(S) URLs are allowed")
    host = parts.hostname.rstrip(".").lower()
    if not any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains):
        raise CampusNewsSourceError(f"URL host is outside the official allowlist: {host}")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


async def fetch_source(source: CampusNewsSource, timeout_seconds: float) -> tuple[NormalizedCampusNewsItem, ...]:
    async with httpx.AsyncClient(timeout=max(0.5, timeout_seconds), follow_redirects=False) as client:
        current_url = source.url
        for hop in range(MAX_REDIRECTS + 1):
            async with client.stream("GET", current_url, headers={"User-Agent": "CampusAgentNews/1.0"}) as response:
                if response.is_redirect:
                    if hop == MAX_REDIRECTS or not response.headers.get("location"):
                        raise CampusNewsSourceError("too many or malformed redirects")
                    current_url = validate_official_url(urljoin(current_url, response.headers["location"]), source.allowed_domains)
                    continue
                response.raise_for_status()
                declared_size = response.headers.get("content-length")
                if declared_size and declared_size.isdigit() and int(declared_size) > MAX_RESPONSE_BYTES:
                    raise CampusNewsSourceError("campus news response is too large")
                chunks: list[bytes] = []
                received = 0
                async for chunk in response.aiter_bytes():
                    received += len(chunk)
                    if received > MAX_RESPONSE_BYTES:
                        raise CampusNewsSourceError("campus news response is too large")
                    chunks.append(chunk)
                final_url = validate_official_url(str(response.url), source.allowed_domains)
                return parse_source_document(source, b"".join(chunks), final_url)
    raise CampusNewsSourceError("campus news source could not be fetched")


def parse_source_document(source: CampusNewsSource, body: bytes, base_url: str | None = None) -> tuple[NormalizedCampusNewsItem, ...]:
    if source.format == "rss":
        raw_items = _parse_feed(body)
    else:
        raw_items = _parse_html(source, body)
    items: list[NormalizedCampusNewsItem] = []
    for raw in raw_items[:MAX_ITEMS_PER_SOURCE]:
        try:
            title = cast(str, _clean_text(raw.get("title"), 300))
            published_at = _parse_date(raw.get("published_at"), source.date_format)
            url = validate_official_url(urljoin(base_url or source.url, raw.get("url") or ""), source.allowed_domains)
            event_end = _parse_date(raw.get("event_end_at"), source.date_format) if raw.get("event_end_at") else None
            summary = _clean_text(raw.get("summary"), 1000, required=False)
        except (CampusNewsSourceError, ValueError, TypeError):
            continue
        fingerprint = hashlib.sha256(f"{url}\n{title}\n{published_at.isoformat()}".encode()).hexdigest()
        items.append(NormalizedCampusNewsItem(
            source_id=source.id, category=source.category, title=title, summary=summary,
            source=source.source, url=url, published_at=published_at,
            event_end_at=event_end, fingerprint=fingerprint,
        ))
    if not items:
        raise CampusNewsSourceError(f"source {source.id} contained no usable items")
    return tuple(items)


def _parse_feed(body: bytes) -> list[dict[str, str | None]]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise CampusNewsSourceError("invalid RSS/Atom XML") from error
    entries = [node for node in root.iter() if _local_name(node.tag) in ("item", "entry")]
    parsed: list[dict[str, str | None]] = []
    for entry in entries:
        values: dict[str, str | None] = {"title": None, "url": None, "published_at": None, "summary": None, "event_end_at": None}
        for child in entry.iter():
            name = _local_name(child.tag)
            text = "".join(child.itertext()).strip()
            if name == "title" and not values["title"]:
                values["title"] = text
            elif name in ("pubDate", "published", "updated", "date") and not values["published_at"]:
                values["published_at"] = text
            elif name in ("description", "summary") and not values["summary"]:
                values["summary"] = text
            elif name == "link" and not values["url"]:
                values["url"] = child.attrib.get("href") or text
        parsed.append(values)
    return parsed


def _parse_html(source: CampusNewsSource, body: bytes) -> list[dict[str, str | None]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as error:  # pragma: no cover - dependency declared for production
        raise CampusNewsSourceError("beautifulsoup4 is required for HTML campus news sources") from error
    soup = BeautifulSoup(body, "html.parser")
    parsed: list[dict[str, str | None]] = []
    for node in soup.select(source.item_selector or ""):
        title_node = node.select_one(source.title_selector or "")
        date_node = node.select_one(source.date_selector or "")
        link_node = node.select_one(source.link_selector or "")
        summary_node = node.select_one(source.summary_selector) if source.summary_selector else None
        end_node = node.select_one(source.event_end_selector) if source.event_end_selector else None
        parsed.append({
            "title": title_node.get_text(" ", strip=True) if title_node else None,
            "published_at": date_node.get_text(" ", strip=True) if date_node else None,
            "url": link_node.get("href") if link_node else None,
            "summary": summary_node.get_text(" ", strip=True) if summary_node else None,
            "event_end_at": end_node.get_text(" ", strip=True) if end_node else None,
        })
    return parsed


def _parse_date(value: str | None, date_format: str | None) -> datetime:
    if not value:
        raise ValueError("missing date")
    if date_format:
        parsed = datetime.strptime(value.strip(), date_format)
    else:
        try:
            parsed = parsedate_to_datetime(value.strip())
        except (TypeError, ValueError):
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)


def _required_text(entry: dict, name: str, limit: int) -> str:
    value = _optional_text(entry, name, limit)
    if not value:
        raise CampusNewsSourceError(f"{name} is required")
    return value


def _optional_text(entry: dict, name: str, limit: int) -> str | None:
    value = entry.get(name)
    if value is None:
        return None
    if not isinstance(value, str) or len(value.strip()) > limit:
        raise CampusNewsSourceError(f"{name} must be a string of at most {limit} characters")
    return value.strip() or None


def _clean_text(value: str | None, limit: int, required: bool = True) -> str | None:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    if required and not cleaned:
        raise CampusNewsSourceError("required text is missing")
    return cleaned[:limit] or None


def _normalize_domain(value: object) -> str:
    if not isinstance(value, str):
        raise CampusNewsSourceError("allowed domain values must be strings")
    domain = value.strip().lower().rstrip(".")
    if not domain or ":" in domain or "/" in domain:
        raise CampusNewsSourceError(f"invalid allowed domain: {value}")
    return domain


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
