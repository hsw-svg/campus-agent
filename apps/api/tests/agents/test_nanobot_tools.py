"""Focused tests for custom tools exposed to nanobot."""

import json

import pytest

from app.agents.nanobot.tools.bing_search import BingSearchTool
from app.agents.nanobot.tools.slide_validator import SlideDeckValidatorTool
from app.integrations.search.bing import SearchItem, SearchResult


class _BingStub:
    def __init__(self, *, configured: bool, result: SearchResult) -> None:
        self.is_configured = configured
        self.result = result
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, count: int = 5) -> SearchResult:
        self.calls.append((query, count))
        return self.result


@pytest.mark.asyncio
async def test_bing_search_tool_formats_configured_results() -> None:
    provider = _BingStub(
        configured=True,
        result=SearchResult(
            available=True,
            items=(
                SearchItem("Python 教程", "https://example.com/python", "切片示例"),
                SearchItem("岗位要求", "https://example.com/job", ""),
            ),
        ),
    )

    result = await BingSearchTool(provider).execute(query="Python 切片", count=2)

    assert result.is_error is False
    assert provider.calls == [("Python 切片", 2)]
    assert "Search results for: Python 切片" in result
    assert "1. Python 教程" in result
    assert "URL: https://example.com/python" in result
    assert "切片示例" in result
    assert "2. 岗位要求" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("configured", "available", "expected"),
    [
        (False, False, "not configured"),
        (True, False, "temporarily unavailable"),
    ],
)
async def test_bing_search_tool_flags_unconfigured_or_unavailable(
    configured: bool, available: bool, expected: str
) -> None:
    provider = _BingStub(
        configured=configured,
        result=SearchResult(available=available, items=()),
    )

    result = await BingSearchTool(provider).execute(query="topic")

    assert result.is_error is True
    assert expected in result
    assert provider.calls == ([] if not configured else [("topic", 5)])


@pytest.mark.asyncio
async def test_bing_search_tool_treats_no_results_as_non_error() -> None:
    provider = _BingStub(
        configured=True,
        result=SearchResult(available=True, items=()),
    )

    result = await BingSearchTool(provider).execute(query="missing")

    assert result.is_error is False
    assert result == "No results found for: missing"


def _deck(*, slide_count: int, include_quality_signals: bool) -> str:
    layouts = ("title", "bullets", "two_column", "callout", "summary")
    slides = []
    for index in range(slide_count):
        slide = {
            "index": index + 1,
            "layout": layouts[index % len(layouts)] if include_quality_signals else "bullets",
            "title": f"第 {index + 1} 页",
            "bullets": ["内容"],
        }
        if include_quality_signals and index == 0:
            slide["media"] = [{"kind": "image", "url": "https://example.com/image.png"}]
            slide["citations"] = [{"title": "来源", "url": "https://example.com/source"}]
        slides.append(slide)
    return json.dumps({"topic": "测试课件", "slides": slides}, ensure_ascii=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["", "not-json", "[]"])
async def test_slide_validator_flags_empty_or_invalid_input(value: str) -> None:
    result = await SlideDeckValidatorTool().execute(json_content=value)

    assert result.is_error is True
    assert "JSON content" in result or "Validation failed" in result


@pytest.mark.asyncio
async def test_slide_validator_returns_quality_warnings() -> None:
    result = await SlideDeckValidatorTool().execute(
        json_content=_deck(slide_count=2, include_quality_signals=False)
    )

    assert result.is_error is False
    assert result.startswith("Validation passed with warnings:")
    assert "Only 2 slides" in result
    assert "Only 1 different layouts" in result
    assert "No media suggestions found" in result
    assert "No citations found" in result


@pytest.mark.asyncio
async def test_slide_validator_accepts_valid_high_quality_deck() -> None:
    result = await SlideDeckValidatorTool().execute(
        json_content=_deck(slide_count=8, include_quality_signals=True)
    )

    assert result.is_error is False
    assert result == "Validation passed. Slide deck structure is good."
