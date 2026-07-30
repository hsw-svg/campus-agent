"""Focused coverage for the nanobot configuration and runner adapter."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from nanobot.agent.runner import AgentRunResult

from app.agents.contracts import (
    AgentContext,
    AgentRequest,
    ContextArtifact,
    ContextSource,
)
from app.agents.nanobot.config import build_nanobot_config
from app.agents.nanobot.runner import NanobotRunner
from app.core.config import Settings
from app.integrations.search.bing import BingSearchProvider


def _request(*, content: str = "生成 Python 课件", context: AgentContext | None = None) -> AgentRequest:
    return AgentRequest(
        workspace_id=uuid4(),
        conversation_id=uuid4(),
        role="teacher",
        agent_id="course_iteration",
        content=content,
        context=context or AgentContext(),
    )


def test_build_nanobot_config_maps_deepseek_provider_and_model() -> None:
    settings = Settings(
        chat_base_url="https://deepseek.example/v1",
        chat_api_key="secret-key",
        chat_model="deepseek-chat",
    )

    config = build_nanobot_config(settings)

    assert config.providers.deepseek.api_base == "https://deepseek.example/v1"
    assert config.providers.deepseek.api_key == "secret-key"
    assert config.agents.defaults.provider == "deepseek"
    assert config.agents.defaults.model == "deepseek-chat"


def test_runner_converts_supported_context_artifacts_to_user_message() -> None:
    artifacts = (
        ContextArtifact(uuid4(), "learning_analysis", "学情", "切片掌握薄弱", {}),
        ContextArtifact(uuid4(), "classroom_summary", "课堂", "需要增加演示", {}),
        ContextArtifact(uuid4(), "grading", "批改", "边界错误较多", {}),
        ContextArtifact(uuid4(), "slide_deck", "旧课件", "不应注入", {}),
    )
    request = _request(
        context=AgentContext(
            messages=({"role": "assistant", "content": "历史消息"},),
            selected_artifacts=artifacts,
        )
    )
    runner = NanobotRunner(build_nanobot_config(Settings()))

    messages = runner._build_messages(request, "system instructions")

    assert messages[0] == {"role": "system", "content": "system instructions"}
    assert messages[1]["role"] == "user"
    assert "[learning_analysis] 切片掌握薄弱" in messages[1]["content"]
    assert "[classroom_summary] 需要增加演示" in messages[1]["content"]
    assert "[grading] 边界错误较多" in messages[1]["content"]
    assert "不应注入" not in messages[1]["content"]
    assert "历史消息" not in messages[1]["content"]
    assert messages[1]["content"].endswith(request.content)


def test_runner_includes_previous_deck_for_iteration() -> None:
    original = _request()
    request = AgentRequest(
        workspace_id=original.workspace_id,
        conversation_id=original.conversation_id,
        role=original.role,
        agent_id=original.agent_id,
        content=original.content,
        context=original.context,
        previous_slide_deck={"topic": "旧课件", "data": {"slides": [1]}},
    )
    runner = NanobotRunner(build_nanobot_config(Settings()))

    messages = runner._build_messages(request, "system instructions")

    assert '[previous_slide_deck] {"topic": "旧课件"' in messages[1]["content"]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("react", 20), ("plan_and_solve", 10), ("reflection", 6), ("unknown", 20)],
)
def test_runner_mode_iteration_limits(mode: str, expected: int) -> None:
    runner = NanobotRunner(build_nanobot_config(Settings()))

    assert runner._get_max_iterations(mode) == expected


def test_runner_registers_validator_and_only_configured_bing() -> None:
    config = build_nanobot_config(Settings())

    without_bing = NanobotRunner(config)._get_tools()
    unconfigured = NanobotRunner(config, BingSearchProvider(api_key=None))._get_tools()
    configured = NanobotRunner(config, BingSearchProvider(api_key="key"))._get_tools()

    assert without_bing.tool_names == ["slide_deck_validator"]
    assert unconfigured.tool_names == ["slide_deck_validator"]
    assert configured.tool_names == ["bing_search", "slide_deck_validator"]


@pytest.mark.asyncio
async def test_runner_constructs_agent_run_spec_and_converts_result(monkeypatch) -> None:
    settings = Settings(
        chat_base_url="https://deepseek.example/v1",
        chat_api_key="key",
        chat_model="deepseek-chat",
    )
    config = build_nanobot_config(settings)
    config.agents.defaults.max_tool_result_chars = 4321
    config.agents.defaults.fail_on_tool_error = False
    config.agents.defaults.context_block_limit = 7
    config.agents.defaults.provider_retry_mode = "none"
    source = ContextSource(uuid4(), "source.md", "source excerpt", 2)
    request = _request(context=AgentContext(sources=(source,)))
    payload = '{"topic":"Python 切片","slides":[{"index":1,"title":"导入"}]}'
    nanobot_result = AgentRunResult(
        final_content=payload,
        messages=[],
        error="one tool failed",
    )
    provider_snapshot = object()
    runtime = object()
    captured: dict[str, object] = {}

    def fake_build_provider_snapshot(actual_config):
        captured["config"] = actual_config
        return provider_snapshot

    def fake_runtime_from_provider_snapshot(actual_snapshot):
        captured["snapshot"] = actual_snapshot
        return runtime

    class FakeAgentRunner:
        async def run(self, spec):
            captured["spec"] = spec
            return nanobot_result

    monkeypatch.setattr("app.agents.nanobot.runner.build_provider_snapshot", fake_build_provider_snapshot)
    monkeypatch.setattr(
        "app.agents.nanobot.runner.runtime_from_provider_snapshot",
        fake_runtime_from_provider_snapshot,
    )
    monkeypatch.setattr("app.agents.nanobot.runner.AgentRunner", FakeAgentRunner)

    result = await NanobotRunner(config, BingSearchProvider(api_key="key")).execute(
        request, mode="reflection"
    )

    spec = captured["spec"]
    assert captured["config"] is config
    assert captured["snapshot"] is provider_snapshot
    assert spec.runtime is runtime
    assert spec.initial_messages[0]["role"] == "system"
    assert "[执行模式：Reflection]" in spec.initial_messages[0]["content"]
    assert spec.initial_messages[1] == {"role": "user", "content": request.content}
    assert spec.tools.tool_names == ["bing_search", "slide_deck_validator"]
    assert spec.max_iterations == 6
    assert spec.max_tool_result_chars == 4321
    assert spec.fail_on_tool_error is False
    assert spec.workspace == Path(config.workspace_path)
    assert spec.context_block_limit == 7
    assert spec.provider_retry_mode == "none"

    assert result.text == payload
    assert result.structured_data == {
        "topic": "Python 切片",
        "slides": [{"index": 1, "title": "导入"}],
    }
    assert result.artifact is not None
    assert result.artifact.type == "slide_deck"
    assert result.artifact.title == "Python 切片"
    assert result.artifact.data == result.structured_data
    assert result.artifact.content == payload
    assert result.artifact.format == "json"
    assert result.citations == (source,)
    assert result.warnings == ("one tool failed",)


def test_runner_leaves_non_json_final_content_unstructured() -> None:
    request = _request(content="普通回复")
    result = NanobotRunner(build_nanobot_config(Settings()))._to_agent_result(
        SimpleNamespace(final_content="plain text", error=None), request
    )

    assert result.text == "plain text"
    assert result.structured_data is None
    assert result.artifact is None
    assert result.warnings == ()
