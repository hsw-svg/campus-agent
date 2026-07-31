from datetime import datetime, timedelta, timezone

import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.campus_news.models import CampusNewsSourceState
from app.campus_news.repositories import CampusNewsRepository
from app.db.base import Base
from app.integrations.campus_news import (
    CampusNewsSourceError,
    NormalizedCampusNewsItem,
    fetch_source,
    parse_source_document,
    parse_sources,
    validate_official_url,
)
from app.services import campus_news as service


SOURCE_JSON = """[
  {
    "id": "official-news",
    "category": "news",
    "source": "校园新闻网",
    "format": "rss",
    "url": "https://news.example.edu.cn/feed.xml",
    "allowed_domains": ["example.edu.cn"]
  }
]"""


def test_source_config_and_feed_normalization_reject_non_official_links() -> None:
    source = parse_sources(SOURCE_JSON)[0]
    body = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss><channel>
      <item><title> Official update </title><pubDate>Wed, 30 Jul 2026 08:00:00 +0800</pubDate><link>/news/1</link><description> Summary </description></item>
      <item><title>Copied update</title><pubDate>2026-07-30T08:00:00+08:00</pubDate><link>https://example.com/copied</link></item>
    </channel></rss>"""

    items = parse_source_document(source, body, source.url)

    assert len(items) == 1
    assert items[0].title == "Official update"
    assert items[0].url == "https://news.example.edu.cn/news/1"
    assert items[0].published_at.tzinfo is not None


def test_source_config_requires_explicit_official_allowlist() -> None:
    with pytest.raises(CampusNewsSourceError):
        parse_sources(SOURCE_JSON.replace('"allowed_domains": ["example.edu.cn"]', '"allowed_domains": []'))
    with pytest.raises(CampusNewsSourceError):
        validate_official_url("file:///etc/passwd", ("example.edu.cn",))
    with pytest.raises(CampusNewsSourceError):
        validate_official_url("https://example.edu.cn.evil.test/news", ("example.edu.cn",))


def test_selector_driven_html_source_parses_relative_official_links() -> None:
    source = parse_sources("""[{
      "id": "official-notices", "category": "notice", "source": "通知公告",
      "format": "html", "url": "https://www.example.edu.cn/notices",
      "allowed_domains": ["example.edu.cn"], "item_selector": ".notice",
      "title_selector": ".title", "date_selector": "time", "link_selector": "a",
      "summary_selector": ".summary", "date_format": "%Y-%m-%d"
    }]""")[0]
    body = b"""<ul>
      <li class="notice"><a href="/notice/1"><span class="title">Service notice</span></a><time>2026-07-30</time><p class="summary">Schedule updated</p></li>
      <li class="notice"><a href="https://evil.test/notice/2"><span class="title">Copied notice</span></a><time>2026-07-30</time></li>
    </ul>"""

    items = parse_source_document(source, body, source.url)

    assert len(items) == 1
    assert items[0].url == "https://www.example.edu.cn/notice/1"
    assert items[0].summary == "Schedule updated"


@pytest.mark.asyncio
async def test_fetch_validates_redirect_target_before_following(monkeypatch: pytest.MonkeyPatch) -> None:
    source = parse_sources(SOURCE_JSON)[0]
    real_client = httpx.AsyncClient
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/feed.xml":
            return httpx.Response(302, headers={"location": "/final.xml"})
        return httpx.Response(200, content=b"<rss><channel><item><title>News</title><pubDate>2026-07-30T00:00:00Z</pubDate><link>/news/1</link></item></channel></rss>")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    items = await fetch_source(source, 1)
    assert len(items) == 1
    assert requested_paths == ["/feed.xml", "/final.xml"]

    def external_redirect(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://evil.test/feed.xml"})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(external_redirect), **kwargs))
    with pytest.raises(CampusNewsSourceError):
        await fetch_source(source, 1)


@pytest.mark.asyncio
async def test_live_cache_survives_refresh_failure_and_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    now = datetime(2026, 7, 30, 12, tzinfo=timezone.utc)
    source = parse_sources(SOURCE_JSON)[0]
    item = NormalizedCampusNewsItem(
        source_id=source.id,
        category="news",
        title="Latest official news",
        summary=None,
        source=source.source,
        url="https://news.example.edu.cn/news/1",
        published_at=now,
        event_end_at=None,
        fingerprint="a" * 64,
    )

    async def succeeds(_source, _timeout):
        return (item,)

    async def fails(_source, _timeout):
        raise TimeoutError("upstream timed out")

    with Session(engine) as session:
        repository = CampusNewsRepository(session)
        monkeypatch.setattr(service, "fetch_source", succeeds)
        response, _ = await service.live_response(
            repository, (source,), refresh_seconds=1800, max_stale_seconds=604800,
            timeout_seconds=1, now=now,
        )
        assert response["status"] == "fresh"
        assert [entry["title"] for entry in response["items"]] == ["Latest official news"]

        monkeypatch.setattr(service, "fetch_source", fails)
        await service.refresh_sources(repository, (source,), timeout_seconds=1, now=now + timedelta(hours=1))
        response, _ = await service.live_response(
            repository, (source,), refresh_seconds=1800, max_stale_seconds=604800,
            timeout_seconds=1, now=now + timedelta(hours=1),
        )
        assert response["status"] == "degraded"
        assert len(response["items"]) == 1

        state = session.get(CampusNewsSourceState, source.id)
        assert state is not None
        state.last_success_at = now - timedelta(days=8)
        session.commit()
        response, _ = await service.live_response(
            repository, (source,), refresh_seconds=1800, max_stale_seconds=604800,
            timeout_seconds=1, now=now,
        )
        assert response["status"] == "degraded"
        assert response["items"] == []
