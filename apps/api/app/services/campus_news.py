from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.campus_news.models import CampusNewsItem, CampusNewsSourceState
from app.campus_news.repositories import CampusNewsRepository
from app.integrations.campus_news import CampusNewsSource, fetch_source


def sample_response(now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    entries = (
        ("news", "校园教学成果交流活动顺利举行", "校园新闻网", "多项教学创新成果集中交流展示。"),
        ("news", "图书馆推出新学期学习支持服务", "校园新闻网", "学习空间与资源咨询服务进一步开放。"),
        ("news", "校园志愿服务项目完成阶段总结", "校园新闻网", "师生志愿团队分享服务经验与成果。"),
        ("activity", "学术写作与资料检索专题讲座", "校园活动", "面向全体学生开放，介绍高效检索与写作方法。"),
        ("activity", "校园体育文化体验周", "校园活动", "多项轻量运动体验活动将在校内开展。"),
        ("activity", "学生创新作品交流展", "校园活动", "集中展示跨学科创新实践作品。"),
        ("notice", "近期教学服务安排通知", "通知公告", "请同学们关注相关服务时间安排。"),
        ("notice", "公共学习空间使用提示", "通知公告", "使用公共空间时请遵守开放与预约规则。"),
        ("notice", "校园网络维护安排", "通知公告", "维护期间部分网络服务可能短时波动。"),
    )
    items = []
    counters = {"news": 0, "activity": 0, "notice": 0}
    for index, (category, title, source, summary) in enumerate(entries):
        counters[category] += 1
        items.append({
            "id": f"sample-{category}-{counters[category]}",
            "category": category,
            "title": title,
            "published_at": now - timedelta(days=index // 3),
            "event_end_at": None,
            "source": source,
            "summary": summary,
            "url": None,
        })
    return {"mode": "sample", "status": "fresh", "refreshing": False, "last_success_at": None, "items": items}


async def live_response(
    repository: CampusNewsRepository,
    sources: tuple[CampusNewsSource, ...],
    *,
    refresh_seconds: int,
    max_stale_seconds: int,
    timeout_seconds: float,
    now: datetime | None = None,
) -> tuple[dict[str, Any], bool]:
    now = now or datetime.now(timezone.utc)
    source_ids = tuple(source.id for source in sources)
    states = repository.states(source_ids)
    cached = repository.list_items(source_ids)
    cold_sources = tuple(source for source in sources if not any(item.source_id == source.id for item in cached))
    if cold_sources:
        await refresh_sources(repository, cold_sources, timeout_seconds=timeout_seconds, now=now)
        states = repository.states(source_ids)
        cached = repository.list_items(source_ids)

    stale_sources = tuple(
        source for source in sources
        if not _is_fresh(states.get(source.id), now, refresh_seconds)
    )
    response = _assemble_live(cached, states, source_ids, now, max_stale_seconds)
    should_refresh = bool(stale_sources and not cold_sources)
    response["refreshing"] = should_refresh
    if should_refresh and response["status"] == "fresh":
        response["status"] = "stale"
    return response, should_refresh


async def refresh_sources(
    repository: CampusNewsRepository,
    sources: tuple[CampusNewsSource, ...],
    *,
    timeout_seconds: float,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(timezone.utc)
    for source in sources:
        if not repository.acquire_refresh_lease(source.id, now):
            continue
        try:
            items = await fetch_source(source, timeout_seconds)
        except Exception as error:  # noqa: BLE001 - upstream failures deliberately degrade
            repository.mark_failure(source.id, f"{type(error).__name__}: {error}", now)
            continue
        repository.replace_source(source.id, items, now)


async def refresh_in_background(
    session_factory: sessionmaker[Session],
    sources: tuple[CampusNewsSource, ...],
    timeout_seconds: float,
) -> None:
    with session_factory() as session:
        await refresh_sources(
            CampusNewsRepository(session), sources, timeout_seconds=timeout_seconds
        )


def invalid_config_response() -> dict[str, Any]:
    return {"mode": "live", "status": "degraded", "refreshing": False, "last_success_at": None, "items": []}


def _assemble_live(
    cached: list[CampusNewsItem],
    states: dict[str, CampusNewsSourceState],
    source_ids: tuple[str, ...],
    now: datetime,
    max_stale_seconds: int,
) -> dict[str, Any]:
    usable_sources = {
        source_id for source_id in source_ids
        if (success := _aware(states.get(source_id).last_success_at if states.get(source_id) else None))
        and success >= now - timedelta(seconds=max(0, max_stale_seconds))
    }
    filtered = [
        item for item in cached
        if item.source_id in usable_sources
        and not (item.category == "activity" and _aware(item.event_end_at) and _aware(item.event_end_at) < now)
    ]
    per_category = {"news": 0, "activity": 0, "notice": 0}
    result_items: list[dict[str, Any]] = []
    for item in sorted(filtered, key=lambda row: _aware(row.published_at) or now, reverse=True):
        if per_category[item.category] >= 3:
            continue
        per_category[item.category] += 1
        result_items.append({
            "id": str(item.id), "category": item.category, "title": item.title,
            "published_at": _aware(item.published_at), "event_end_at": _aware(item.event_end_at),
            "source": item.source, "summary": item.summary, "url": item.url,
        })
    successes = [_aware(state.last_success_at) for state in states.values() if state.last_success_at]
    degraded = len(usable_sources) < len(source_ids) or any(state.last_error for state in states.values())
    return {
        "mode": "live",
        "status": "degraded" if degraded else "fresh",
        "refreshing": False,
        "last_success_at": max(successes) if successes else None,
        "items": result_items,
    }


def _is_fresh(state: CampusNewsSourceState | None, now: datetime, refresh_seconds: int) -> bool:
    success = _aware(state.last_success_at if state else None)
    return bool(success and success >= now - timedelta(seconds=max(0, refresh_seconds)))


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
