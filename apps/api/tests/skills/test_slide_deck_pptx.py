"""Regression coverage for the slide_deck -> .pptx render skill."""

import io
import zipfile

from app.skills.slide_deck_pptx import SlideDeckPptxSkill


SAMPLE_DECK = {
    "topic": "Python 切片与元组",
    "audience": "计算机学院大二",
    "objective": "掌握切片语法与元组不可变性",
    "duration_minutes": 45,
    "context_signals": {
        "learning_analysis": "上一次作业平均 82，切片题正确率 61%。",
        "weak_points": ["切片负步长"],
        "classroom_summary": "",
        "grading": "",
        "job_skill_focus": ["中级 Python 岗位常考"],
        "industry_updates": [
            {"title": "案例A", "url": "https://example.com/a", "snippet": "..."},
        ],
    },
    "slides": [
        {
            "index": 1,
            "layout": "title",
            "title": "Python 切片与元组",
            "subtitle": "面向大二·45 分钟",
            "bullets": [],
            "notes": "开场 3 秒抢答",
            "key_points": [],
            "citations": [],
            "columns": [],
        },
        {
            "index": 2,
            "layout": "bullets",
            "title": "为什么这节课重要",
            "subtitle": "",
            "bullets": ["岗位面试常考", "承接后续 numpy 广播"],
            "notes": "留 30 秒抢答",
            "key_points": ["面试高频"],
            "citations": [{"title": "案例A", "url": "https://example.com/a"}],
            "columns": [],
        },
        {
            "index": 3,
            "layout": "two_column",
            "title": "切片 vs 元组",
            "subtitle": "",
            "bullets": [],
            "notes": "",
            "key_points": [],
            "citations": [],
            "columns": [
                {"title": "切片", "bullets": ["支持负索引", "步长"]},
                {"title": "元组", "bullets": ["不可变", "可作为 key"]},
            ],
        },
        {
            "index": 4,
            "layout": "callout",
            "title": "重点提醒",
            "subtitle": "",
            "bullets": ["切片返回浅拷贝"],
            "notes": "",
            "key_points": [],
            "citations": [],
            "columns": [],
        },
        {
            "index": 5,
            "layout": "summary",
            "title": "小结",
            "subtitle": "",
            "bullets": ["切片语法", "元组特性"],
            "notes": "",
            "key_points": [],
            "citations": [],
            "columns": [],
        },
    ],
    "sources": [{"title": "案例A", "url": "https://example.com/a", "snippet": "..."}],
}


def test_slide_deck_pptx_is_a_valid_zip_with_expected_slide_count() -> None:
    exported = SlideDeckPptxSkill().run(SAMPLE_DECK)

    assert exported.extension == "pptx"
    assert exported.media_type.endswith("presentationml.presentation")
    # PPTX files are ZIP archives; the first two bytes must be the ZIP magic.
    assert exported.content[:2] == b"PK"

    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        slide_files = [
            name
            for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
    # One semantic slide maps to one PPTX page; no implicit cover is added.
    assert len(slide_files) == len(SAMPLE_DECK["slides"])
