"""Validate and normalise slide_deck JSON produced by the LLM."""

from __future__ import annotations

import json
from typing import Any

from app.core.errors import AppError

ALLOWED_LAYOUTS: frozenset[str] = frozenset(
    {"title", "bullets", "two_column", "callout", "summary"}
)


class SlideDeckJsonSkill:
    id = "slide_deck_json"
    version = "1"
    input_type = "str|dict"
    output_type = "dict"
    error_codes = ("slide_deck_json_invalid",)
    has_side_effects = False
    can_access_workspace = False

    def run(self, value: str | dict[str, Any]) -> dict[str, Any]:
        payload = _coerce_json(value)
        return _normalise(payload)


def _coerce_json(value: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise AppError(
            code="slide_deck_json_invalid",
            message="Slide deck payload must be a JSON object.",
            status_code=422,
        )
    text = value.strip()
    if not text:
        raise AppError(
            code="slide_deck_json_invalid",
            message="Slide deck payload is empty.",
            status_code=422,
        )
    # Tolerate accidental code fences from LLMs.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise AppError(
            code="slide_deck_json_invalid",
            message="Slide deck payload is not valid JSON.",
            status_code=422,
            details={"error": str(error)},
        ) from error
    if not isinstance(parsed, dict):
        raise AppError(
            code="slide_deck_json_invalid",
            message="Slide deck payload must be a JSON object.",
            status_code=422,
        )
    return parsed


def _normalise(payload: dict[str, Any]) -> dict[str, Any]:
    topic = str(payload.get("topic") or "").strip()
    raw_slides = payload.get("slides")
    if not topic:
        raise AppError(
            code="slide_deck_json_invalid",
            message="Slide deck payload is missing 'topic'.",
            status_code=422,
        )
    if not isinstance(raw_slides, list) or not raw_slides:
        raise AppError(
            code="slide_deck_json_invalid",
            message="Slide deck payload must contain a non-empty 'slides' list.",
            status_code=422,
        )
    slides = [_normalise_slide(item, index + 1) for index, item in enumerate(raw_slides)]
    slides.sort(key=lambda item: item["index"])
    for pos, slide in enumerate(slides, start=1):
        slide["index"] = pos
    context_signals = _normalise_context_signals(payload.get("context_signals"))
    sources = _normalise_sources(payload.get("sources"))
    return {
        "topic": topic,
        "audience": str(payload.get("audience") or "").strip(),
        "objective": str(payload.get("objective") or "").strip(),
        "duration_minutes": _coerce_int(payload.get("duration_minutes")),
        "template_id": str(payload.get("template_id") or "").strip(),
        "context_signals": context_signals,
        "slides": slides,
        "sources": sources,
    }


def _normalise_slide(item: Any, fallback_index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AppError(
            code="slide_deck_json_invalid",
            message="Each slide entry must be an object.",
            status_code=422,
        )
    layout_raw = str(item.get("layout") or "bullets").strip().lower()
    layout = layout_raw if layout_raw in ALLOWED_LAYOUTS else "bullets"
    index = _coerce_int(item.get("index")) or fallback_index
    return {
        "index": index,
        "layout": layout,
        "title": str(item.get("title") or "").strip(),
        "subtitle": str(item.get("subtitle") or "").strip(),
        "bullets": _string_list(item.get("bullets")),
        "notes": str(item.get("notes") or "").strip(),
        "key_points": _string_list(item.get("key_points")),
        "citations": _normalise_sources(item.get("citations")),
        "media": _normalise_media(item.get("media")),
        "columns": _normalise_columns(item.get("columns")),
    }


def _normalise_context_signals(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "learning_analysis": "",
            "weak_points": [],
            "classroom_summary": "",
            "grading": "",
            "job_skill_focus": [],
            "industry_updates": [],
        }
    return {
        "learning_analysis": str(value.get("learning_analysis") or "").strip(),
        "weak_points": _string_list(value.get("weak_points")),
        "classroom_summary": str(value.get("classroom_summary") or "").strip(),
        "grading": str(value.get("grading") or "").strip(),
        "job_skill_focus": _string_list(value.get("job_skill_focus")),
        "industry_updates": _normalise_sources(value.get("industry_updates")),
    }


def _normalise_sources(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        url = str(entry.get("url") or "").strip()
        snippet = str(entry.get("snippet") or "").strip()
        if not title and not url and not snippet:
            continue
        result.append({"title": title, "url": url, "snippet": snippet})
    return result


def _normalise_columns(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    columns: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        columns.append(
            {
                "title": str(entry.get("title") or "").strip(),
                "bullets": _string_list(entry.get("bullets")),
            }
        )
    return columns


def _normalise_media(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    media_items: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind") or "").strip().lower()
        url = str(entry.get("url") or "").strip()
        if not kind and not url:
            continue
        media_items.append(
            {
                "kind": kind if kind in {"image", "video", "gif", "embed", "animation"} else "image",
                "url": url,
                "title": str(entry.get("title") or "").strip(),
                "caption": str(entry.get("caption") or "").strip(),
                "alt": str(entry.get("alt") or "").strip(),
                "poster": str(entry.get("poster") or "").strip(),
                "placement": str(entry.get("placement") or "inline").strip().lower() or "inline",
                "autoplay": bool(entry.get("autoplay")),
                "loop": bool(entry.get("loop")),
                "muted": bool(entry.get("muted")),
                "start_ms": _coerce_int(entry.get("start_ms")),
                "end_ms": _coerce_int(entry.get("end_ms")),
            }
        )
    return media_items


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _coerce_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
