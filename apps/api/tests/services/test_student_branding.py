import pytest

from app.services.student_branding import (
    StudentBrandStreamFilter,
    normalize_student_visible_text,
)


@pytest.mark.parametrize(
    ("chunks", "expected"),
    [
        (["Deep", "Tutor助手发现了重点。"], "AI 学伴发现了重点。"),
        (["deep ", "tutor助教建议画图。"], "AI 学伴建议画图。"),
        (["DEE", "PTUTOR 提供了线索。"], "智汇校园 提供了线索。"),
        (["普通回答，不含内部品牌。"], "普通回答，不含内部品牌。"),
    ],
)
def test_student_brand_stream_filter_handles_arbitrary_brand_splits(
    chunks: list[str],
    expected: str,
) -> None:
    brand_filter = StudentBrandStreamFilter()
    emitted = [brand_filter.feed(chunk) for chunk in chunks]
    emitted.append(brand_filter.finish())

    assert "".join(emitted) == expected


def test_complete_text_normalizer_uses_the_same_brand_contract() -> None:
    assert normalize_student_visible_text(
        "DeepTutor助手发现一处问题，Deep Tutor 建议重试。"
    ) == "AI 学伴发现一处问题，智汇校园 建议重试。"
