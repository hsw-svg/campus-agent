"""Stable slide ID normalization contract."""

import pytest

from app.core.errors import AppError
from app.skills.slide_deck_json import SlideDeckJsonSkill


def _deck(slides: list[dict]) -> dict:
    return {"topic": "测试课件", "slides": slides}


def test_legacy_deck_gets_deterministic_ids_after_index_ordering() -> None:
    value = _deck(
        [
            {"index": 2, "title": "第二页"},
            {"index": 1, "title": "第一页"},
        ]
    )

    first = SlideDeckJsonSkill().run(value)
    second = SlideDeckJsonSkill().run(value)

    assert [slide["title"] for slide in first["slides"]] == ["第一页", "第二页"]
    assert [slide["id"] for slide in first["slides"]] == ["slide-001", "slide-002"]
    assert first == second


def test_supplied_stable_ids_are_preserved() -> None:
    normalized = SlideDeckJsonSkill().run(
        _deck(
            [
                {"id": "lesson-intro", "index": 1, "title": "导入"},
                {"id": "slide-009", "index": 2, "title": "总结"},
            ]
        )
    )
    assert [slide["id"] for slide in normalized["slides"]] == [
        "lesson-intro",
        "slide-009",
    ]


def test_previous_deck_context_is_preserved() -> None:
    previous = {"topic": "旧课件", "data": {"slides": [{"id": "old-001"}]}}
    normalized = SlideDeckJsonSkill().run(
        {**_deck([{"title": "新版导入"}]), "previous_slide_deck": previous}
    )

    assert normalized["previous_slide_deck"] == previous


def test_duplicate_supplied_ids_are_rejected() -> None:
    with pytest.raises(AppError, match="duplicate slide ID") as error:
        SlideDeckJsonSkill().run(
            _deck(
                [
                    {"id": "slide-001", "title": "导入"},
                    {"id": "slide-001", "title": "总结"},
                ]
            )
        )
    assert error.value.code == "slide_deck_json_invalid"
