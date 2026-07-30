"""Focused staged-generation coverage for CourseIterationExecutorV2."""

import json
from collections import Counter
from uuid import uuid4

import pytest

from app.agents.contracts import AgentContext, AgentRequest, AgentResult, ContextSource
from app.agents.executors.course_iteration import CourseIterationExecutor
from app.agents.executors.course_iteration_v2 import CourseIterationExecutorV2
from app.agents.executors.registry import AgentExecutorRegistry
from app.agents.nanobot.runner import StageCallResult
from app.core.errors import AppError


class _ConfiguredChat:
    is_configured = True


def _request(content: str, *, sources=()) -> AgentRequest:
    return AgentRequest(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        role="teacher",
        agent_id="course_iteration",
        content=content,
        context=AgentContext(sources=sources),
    )


def _outline(count: int = 8) -> dict:
    return {
        "topic": "Python 切片",
        "audience": "大二",
        "objective": "掌握切片",
        "duration_minutes": 45,
        "context_signals": {"weak_points": ["负步长"]},
        "sources": [{"title": "Python docs", "url": "https://docs.python.org"}],
        "plans": [
            {"title": f"页面 {index}", "layout": "title" if index == 1 else "bullets", "purpose": "教学"}
            for index in range(1, count + 1)
        ],
    }


def _slide(slide_id: str, title: str | None = None) -> dict:
    return {
        "id": slide_id,
        "layout": "bullets",
        "title": title or slide_id,
        "subtitle": "",
        "bullets": ["要点"],
        "notes": "讲稿",
        "key_points": [],
        "citations": [{"title": "Python docs", "url": "https://docs.python.org"}],
        "media": [],
        "columns": [],
    }


class _StagedRunner:
    def __init__(self, *, outline_count: int = 8, defects: list[str] | None = None) -> None:
        self.outline_count = outline_count
        self.defects = defects or []
        self.outline_calls: list[tuple[AgentRequest, str]] = []
        self.batch_calls: list[tuple[list[str], bool, dict]] = []
        self.reflection_calls = 0
        self.failures: dict[tuple[str, ...], list[StageCallResult]] = {}
        self.execute_calls = 0

    async def execute(self, request, *, mode="react") -> AgentResult:
        self.execute_calls += 1
        raise AssertionError("staged PPT generation must not call execute")

    async def generate_slide_outline(self, request, *, mode="react"):
        self.outline_calls.append((request, mode))
        return StageCallResult(json.dumps(_outline(self.outline_count), ensure_ascii=False))

    async def generate_slide_batch(
        self, request, *, deck_context, plans, mode="react", correction=False
    ):
        ids = tuple(plan["id"] for plan in plans)
        self.batch_calls.append((list(ids), correction, deck_context))
        queued = self.failures.get(ids)
        if queued:
            return queued.pop(0)
        suffix = "-revised" if deck_context.get("defect_regeneration") else ""
        return StageCallResult(
            json.dumps({"slides": [_slide(item, item + suffix) for item in ids]})
        )

    async def identify_slide_defects(self, request, *, deck_context, slides):
        self.reflection_calls += 1
        return StageCallResult(json.dumps({"defective_ids": self.defects}))


@pytest.mark.asyncio
async def test_non_slide_request_uses_generic_chat(monkeypatch) -> None:
    expected = AgentResult(text="普通课程迭代建议")

    class FakeGenericChatExecutor:
        def __init__(self, provider) -> None:
            pass

        async def execute(self, request):
            return expected

    runner = _StagedRunner()
    monkeypatch.setattr(
        "app.agents.executors.course_iteration_v2.GenericChatExecutor",
        FakeGenericChatExecutor,
    )
    result = await CourseIterationExecutorV2(_ConfiguredChat(), runner, None).execute(
        _request("给我一些课程迭代建议")
    )
    assert result is expected
    assert runner.outline_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "expected_mode"),
    [
        ("请生成 Python 课件", "react"),
        ("请规划 Python 课件大纲", "plan_and_solve"),
        ("请生成高质量精品 Python 课件", "reflection"),
    ],
)
async def test_modes_use_staged_generation(content: str, expected_mode: str) -> None:
    runner = _StagedRunner()
    result = await CourseIterationExecutorV2(_ConfiguredChat(), runner, None).execute(
        _request(content)
    )

    assert runner.outline_calls[0][1] == expected_mode
    assert runner.execute_calls == 0
    assert [slide["id"] for slide in result.structured_data["slides"]] == [
        f"slide-{index:03d}" for index in range(1, 9)
    ]
    assert [ids for ids, _, _ in runner.batch_calls[:4]] == [
        ["slide-001", "slide-002"],
        ["slide-003", "slide-004"],
        ["slide-005", "slide-006"],
        ["slide-007", "slide-008"],
    ]
    assert all(len(ids) <= 2 for ids, _, _ in runner.batch_calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [7, 13])
async def test_outline_count_is_bounded(count: int) -> None:
    runner = _StagedRunner(outline_count=count)
    with pytest.raises(AppError) as error:
        await CourseIterationExecutorV2(_ConfiguredChat(), runner, None).execute(
            _request("生成 PPT")
        )
    assert error.value.code == "slide_deck_stage_invalid"
    assert runner.batch_calls == []


@pytest.mark.asyncio
async def test_batch_retry_then_split_is_bounded_and_keeps_successful_batches() -> None:
    runner = _StagedRunner()
    bad = StageCallResult("not-json")
    runner.failures[("slide-003", "slide-004")] = [bad, bad]
    result = await CourseIterationExecutorV2(_ConfiguredChat(), runner, None).execute(
        _request("生成 PPT")
    )

    counts = Counter(tuple(ids) for ids, _, _ in runner.batch_calls)
    assert counts[("slide-001", "slide-002")] == 1
    assert counts[("slide-003", "slide-004")] == 2
    assert counts[("slide-003",)] == 1
    assert counts[("slide-004",)] == 1
    assert [slide["id"] for slide in result.structured_data["slides"]] == [
        f"slide-{index:03d}" for index in range(1, 9)
    ]


@pytest.mark.asyncio
async def test_length_stop_splits_even_when_batch_json_is_parseable() -> None:
    runner = _StagedRunner()
    payload = json.dumps({"slides": [_slide("slide-001"), _slide("slide-002")]})
    runner.failures[("slide-001", "slide-002")] = [
        StageCallResult(payload, "max_tokens"),
        StageCallResult(payload, "length"),
    ]
    await CourseIterationExecutorV2(_ConfiguredChat(), runner, None).execute(
        _request("生成 PPT")
    )
    assert [ids for ids, _, _ in runner.batch_calls[:4]] == [
        ["slide-001", "slide-002"],
        ["slide-001", "slide-002"],
        ["slide-001"],
        ["slide-002"],
    ]


@pytest.mark.asyncio
async def test_unknown_ids_exhaust_finite_single_slide_attempts() -> None:
    runner = _StagedRunner()
    bad = StageCallResult(json.dumps({"slides": [_slide("unknown")]}))
    runner.failures[("slide-001", "slide-002")] = [bad, bad]
    runner.failures[("slide-001",)] = [bad, bad]
    with pytest.raises(AppError, match="slide-001"):
        await CourseIterationExecutorV2(_ConfiguredChat(), runner, None).execute(
            _request("生成 PPT")
        )
    counts = Counter(tuple(ids) for ids, _, _ in runner.batch_calls)
    assert counts[("slide-001", "slide-002")] == 2
    assert counts[("slide-001",)] == 2
    assert counts[("slide-003", "slide-004")] == 0


@pytest.mark.asyncio
async def test_reflection_regenerates_only_named_ids_once() -> None:
    runner = _StagedRunner(defects=["slide-002", "slide-007"])
    result = await CourseIterationExecutorV2(_ConfiguredChat(), runner, None).execute(
        _request("生成高质量 PPT")
    )

    assert runner.reflection_calls == 1
    regeneration = [ids for ids, _, ctx in runner.batch_calls if ctx.get("defect_regeneration")]
    assert regeneration == [["slide-002"], ["slide-007"]]
    titles = {slide["id"]: slide["title"] for slide in result.structured_data["slides"]}
    assert titles["slide-002"] == "slide-002-revised"
    assert titles["slide-001"] == "slide-001"


@pytest.mark.asyncio
async def test_previous_deck_sources_and_citations_are_preserved() -> None:
    class PreviousDeckRepository:
        def latest_by_conversation(self, workspace_id, conversation_id, artifact_type):
            return type("Artifact", (), {"title": "旧课件", "data": {"slides": [1]}})()

    source = ContextSource(uuid4(), "source.md", "source excerpt", 2)
    runner = _StagedRunner()
    result = await CourseIterationExecutorV2(
        _ConfiguredChat(), runner, lambda: PreviousDeckRepository()
    ).execute(_request("请完善 PPT", sources=(source,)))

    staged_request = runner.outline_calls[0][0]
    assert staged_request.previous_slide_deck == {
        "topic": "旧课件",
        "data": {"slides": [1]},
    }
    context = runner.batch_calls[0][2]
    assert context["previous_slide_deck"] == staged_request.previous_slide_deck
    assert context["request_sources"][0]["title"] == "source.md"
    assert result.citations == (source,)
    assert result.structured_data["previous_slide_deck"] == staged_request.previous_slide_deck
    assert result.structured_data["sources"][0]["title"] == "Python docs"
    assert result.structured_data["sources"][1] == {
        "title": "source.md",
        "url": "",
        "snippet": "source excerpt",
    }
    assert result.structured_data["slides"][0]["citations"][0]["title"] == "Python docs"


def test_registry_chooses_v2_only_when_nanobot_runner_is_injected() -> None:
    chat = _ConfiguredChat()
    runner = _StagedRunner()
    assert isinstance(
        AgentExecutorRegistry(chat).resolve("teacher", "course_iteration"),
        CourseIterationExecutor,
    )
    with_runner = AgentExecutorRegistry(chat, nanobot_runner=runner).resolve(
        "teacher", "course_iteration"
    )
    assert isinstance(with_runner, CourseIterationExecutorV2)
    assert with_runner.nanobot_runner is runner
