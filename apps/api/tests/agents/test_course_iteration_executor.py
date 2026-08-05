"""Behavioural coverage for the CourseIterationExecutor slide_deck branch."""

import json
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from app.agents.contracts import AgentContext, AgentRequest, ContextArtifact
from app.agents.executors.course_iteration import CourseIterationExecutor
from app.integrations.search.bing import BingSearchProvider, SearchItem, SearchResult


class _FakeChatProvider:
    is_configured = True

    def __init__(self, payloads: list[str]) -> None:
        self._payloads = list(payloads)
        self.calls: list[dict] = []

    def stream_reply(self, messages, *, response_format=None) -> AsyncIterator[str]:
        self.calls.append({"messages": list(messages), "response_format": response_format})
        payload = self._payloads.pop(0)

        async def _iter() -> AsyncIterator[str]:
            yield payload

        return _iter()


class _StubBing:
    def __init__(self, configured: bool, industry: SearchResult, jobs: SearchResult) -> None:
        self._configured = configured
        self._industry = industry
        self._jobs = jobs

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def search(self, query: str, count: int = 5, mkt: str = "zh-CN") -> SearchResult:
        if "岗位" in query:
            return self._jobs
        return self._industry


class _StubRepo:
    def __init__(self, previous=None) -> None:
        self._previous = previous
        self.calls = 0

    def latest_by_conversation(self, workspace_id, conversation_id, artifact_type):
        self.calls += 1
        return self._previous


def _request(content: str, *, selected_artifacts=()) -> AgentRequest:
    return AgentRequest(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        role="teacher",
        agent_id="course_iteration",
        content=content,
        context=AgentContext(selected_artifacts=selected_artifacts),
    )


def _valid_payload(topic: str = "Python 切片与元组", extras: dict | None = None) -> str:
    data = {
        "topic": topic,
        "template_id": "ai_tech",
        "audience": "大二",
        "objective": "掌握切片",
        "duration_minutes": 45,
        "context_signals": {
            "learning_analysis": "",
            "weak_points": [],
            "classroom_summary": "",
            "grading": "",
            "job_skill_focus": [],
            "industry_updates": [],
        },
        "slides": [
            {
                "index": 1,
                "layout": "title",
                "title": topic,
                "subtitle": "",
                "bullets": [],
                "notes": "",
                "key_points": [],
                "citations": [],
            },
            {
                "index": 2,
                "layout": "bullets",
                "title": "关键点",
                "bullets": ["切片", "元组"],
                "notes": "",
                "key_points": ["面试高频"],
                "citations": [],
                "media": [
                    {
                        "kind": "video",
                        "url": "https://example.com/demo.mp4",
                        "title": "切片演示",
                        "caption": "演示切片操作过程",
                        "placement": "inline",
                    }
                ],
            },
        ],
        "sources": [],
    }
    if extras:
        data.update(extras)
    return json.dumps(data, ensure_ascii=False)


@pytest.mark.asyncio
async def test_plain_course_iteration_returns_markdown_artifact() -> None:
    text = "## 课程迭代建议\n\n先用直观图像引入，再逐步过渡到形式化定义。"
    chat = _FakeChatProvider([text])
    executor = CourseIterationExecutor(chat, None, artifact_repository_factory=lambda: None)

    result = await executor.execute(
        _request("课程迭代：教学主题是函数极限，迭代目标是增强直观理解。")
    )

    assert result.text == text
    assert result.artifact is not None
    assert result.artifact.type == "course_iteration"
    assert result.artifact.content == text
    assert result.artifact.format == "markdown"


@pytest.mark.asyncio
async def test_slide_deck_stream_emits_safe_progress_before_final_result() -> None:
    chat = _FakeChatProvider([_valid_payload()])
    bing = _StubBing(False, SearchResult(False, ()), SearchResult(False, ()))
    executor = CourseIterationExecutor(chat, bing, artifact_repository_factory=lambda: None)

    events = [event async for event in executor.stream(_request("请生成一份 Python 切片 课件"))]
    statuses = [event.progress for event in events if event.type == "status" and event.progress]
    result_events = [event.result for event in events if event.type == "result" and event.result]

    assert {status.phase for status in statuses} >= {"retrieval", "model", "validation", "artifact"}
    assert result_events and result_events[0].artifact is not None
    assert all("匿名" not in (status.detail or "") for status in statuses)


@pytest.mark.asyncio
async def test_slide_deck_degrades_when_bing_is_not_configured() -> None:
    chat = _FakeChatProvider([_valid_payload()])
    bing = _StubBing(False, SearchResult(False, ()), SearchResult(False, ()))
    executor = CourseIterationExecutor(chat, bing, artifact_repository_factory=lambda: None)

    result = await executor.execute(_request("请生成一份 Python 切片 课件"))

    assert result.artifact is not None
    assert result.artifact.type == "slide_deck"
    assert any("联网检索未启用" in warning for warning in result.warnings)
    assert result.artifact.data["slides"]


@pytest.mark.asyncio
async def test_slide_deck_happy_path_with_bing_signals() -> None:
    industry = SearchResult(
        True,
        (SearchItem("行业案例A", "https://example.com/a", "..."),),
    )
    jobs = SearchResult(
        True,
        (SearchItem("岗位技能", "https://example.com/j", "初级 Python"),),
    )
    chat = _FakeChatProvider([_valid_payload()])
    bing = _StubBing(True, industry, jobs)
    executor = CourseIterationExecutor(chat, bing, artifact_repository_factory=lambda: None)

    result = await executor.execute(_request("围绕 切片 生成 8 页课件"))

    assert result.artifact is not None
    signals = result.artifact.data["context_signals"]
    assert signals["industry_updates"]
    assert signals["job_skill_focus"]
    assert not result.warnings
    # response_format was requested as json_object
    assert chat.calls[0]["response_format"] == {"type": "json_object"}
    assert result.artifact.data["template_id"] == "ai_tech"
    assert result.artifact.data["template_selection_source"] == "llm"


@pytest.mark.asyncio
async def test_slide_deck_repairs_first_invalid_json() -> None:
    chat = _FakeChatProvider(["not-json", _valid_payload()])
    bing = _StubBing(False, SearchResult(False, ()), SearchResult(False, ()))
    executor = CourseIterationExecutor(chat, bing, artifact_repository_factory=lambda: None)

    result = await executor.execute(_request("请生成 课件"))

    assert result.artifact is not None
    assert len(chat.calls) == 2
    # The retry message referenced the repair instruction.
    retry_prompt = chat.calls[1]["messages"][-1]["content"]
    assert "合法 JSON" in retry_prompt


@pytest.mark.asyncio
async def test_slide_deck_injects_previous_deck_into_prompt() -> None:
    class _PrevArtifact:
        title = "旧课件主题"
        data = {"topic": "旧课件主题", "slides": []}

    chat = _FakeChatProvider([_valid_payload()])
    bing = _StubBing(False, SearchResult(False, ()), SearchResult(False, ()))
    repo = _StubRepo(previous=_PrevArtifact())
    executor = CourseIterationExecutor(chat, bing, artifact_repository_factory=lambda: repo)

    result = await executor.execute(_request("把 课件 改成 6 页"))

    assert repo.calls == 1
    prompt_text = chat.calls[0]["messages"][-1]["content"]
    assert "旧课件主题" in prompt_text
    assert result.artifact is not None


@pytest.mark.asyncio
async def test_explicit_template_name_overrides_model_choice() -> None:
    chat = _FakeChatProvider([_valid_payload(extras={"template_id": "ai_tech"})])
    bing = _StubBing(False, SearchResult(False, ()), SearchResult(False, ()))
    executor = CourseIterationExecutor(chat, bing, artifact_repository_factory=lambda: None)

    result = await executor.execute(_request("使用商业计划书模板生成 Python 课件"))

    assert result.artifact is not None
    assert result.artifact.data["template_id"] == "business_plan"
    assert result.artifact.data["template_name"] == "商业计划书"
    assert result.artifact.data["template_selection_source"] == "explicit"
    prompt_text = chat.calls[0]["messages"][-1]["content"]
    assert '"forced_template_id": "business_plan"' in prompt_text


@pytest.mark.asyncio
async def test_follow_up_keeps_previous_template_without_explicit_switch() -> None:
    class _PrevArtifact:
        title = "上一版"
        data = {"topic": "上一版", "template_id": "business_plan", "slides": []}

    chat = _FakeChatProvider([_valid_payload(extras={"template_id": "ai_tech"})])
    bing = _StubBing(False, SearchResult(False, ()), SearchResult(False, ()))
    repo = _StubRepo(previous=_PrevArtifact())
    executor = CourseIterationExecutor(chat, bing, artifact_repository_factory=lambda: repo)

    result = await executor.execute(_request("把课件压缩到 6 页"))

    assert result.artifact is not None
    assert result.artifact.data["template_id"] == "business_plan"
    assert result.artifact.data["template_selection_source"] == "previous"


@pytest.mark.asyncio
async def test_invalid_model_template_falls_back_to_ai_tech() -> None:
    chat = _FakeChatProvider([_valid_payload(extras={"template_id": "unknown"})])
    bing = _StubBing(False, SearchResult(False, ()), SearchResult(False, ()))
    executor = CourseIterationExecutor(chat, bing, artifact_repository_factory=lambda: None)

    result = await executor.execute(_request("生成一份课程课件"))

    assert result.artifact is not None
    assert result.artifact.data["template_id"] == "ai_tech"
    assert result.artifact.data["template_selection_source"] == "fallback"


@pytest.mark.asyncio
async def test_non_slide_message_wraps_generic_chat_as_course_iteration_artifact(monkeypatch) -> None:
    class _Chat:
        is_configured = True

        def stream_reply(self, messages, *, response_format=None):
            async def _iter():
                yield "普通迭代建议"

            return _iter()

    executor = CourseIterationExecutor(_Chat(), None, artifact_repository_factory=None)

    result = await executor.execute(_request("给我一些课程迭代建议"))

    assert result.text == "普通迭代建议"
    assert result.artifact is not None
    assert result.artifact.type == "course_iteration"
    assert result.artifact.content == result.text
    assert result.artifact.format == "markdown"


def test_bing_provider_is_not_configured_without_key() -> None:
    provider = BingSearchProvider(api_key=None)
    assert provider.is_configured is False
