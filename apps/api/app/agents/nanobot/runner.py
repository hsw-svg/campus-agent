"""NanobotRunner — thin proxy between campus-agent and nanobot's agent runner.

Converts AgentRequest → nanobot agent runner → AgentResult.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from nanobot.agent.runner import AgentRunSpec, AgentRunner
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.config.schema import Config
from nanobot.providers.factory import build_provider_snapshot
from nanobot.utils.llm_runtime import runtime_from_provider_snapshot

from app.agents.contracts import AgentArtifact, AgentRequest, AgentResult
from app.integrations.search.bing import BingSearchProvider


@dataclass(frozen=True)
class StageCallResult:
    """Raw, testable result of one staged model call."""

    text: str
    stop_reason: str | None = None


class NanobotRunner:
    """Thin proxy that delegates LLM execution to nanobot's agent runner.

    Responsibilities:
    - Convert AgentRequest → nanobot message format
    - Select execution mode (react / plan_and_solve / reflection)
    - Invoke nanobot's AgentRunner
    - Convert nanobot output → AgentResult
    """

    def __init__(
        self,
        config: Config,
        bing_provider: BingSearchProvider | None = None,
    ) -> None:
        self._config = config
        self._bing_provider = bing_provider

    async def execute(
        self,
        request: AgentRequest,
        *,
        mode: str = "react",
    ) -> AgentResult:
        """Execute an agent request through nanobot's runner.

        Args:
            request: The campus-agent request.
            mode: Execution mode — 'react', 'plan_and_solve', or 'reflection'.

        Returns:
            AgentResult with text, structured_data, artifact, and warnings.
        """
        # Build system prompt based on mode
        system_prompt = self._build_system_prompt(request, mode)

        # Convert to nanobot message format
        messages = self._build_messages(request, system_prompt)

        provider_snapshot = build_provider_snapshot(self._config)
        runtime = runtime_from_provider_snapshot(provider_snapshot)

        spec = AgentRunSpec(
            initial_messages=messages,
            tools=self._get_tools(),
            runtime=runtime,
            max_iterations=self._get_max_iterations(mode),
            max_tool_result_chars=self._config.agents.defaults.max_tool_result_chars,
            fail_on_tool_error=self._config.agents.defaults.fail_on_tool_error,
            workspace=self._config.workspace_path,
            context_block_limit=self._config.agents.defaults.context_block_limit,
            provider_retry_mode=self._config.agents.defaults.provider_retry_mode,
        )
        result = await AgentRunner().run(spec)

        return self._to_agent_result(result, request)

    async def generate_slide_outline(
        self, request: AgentRequest, *, mode: str = "react"
    ) -> StageCallResult:
        mode_guidance = {
            "react": "先利用可用工具和课程上下文确定真实案例与行业信息。",
            "plan_and_solve": "重点规划导入、核心知识、案例、练习和总结的递进顺序。",
            "reflection": "先生成可供后续一次缺陷检查的完整教学结构。",
        }.get(mode, "")
        prompt = (
            "你正在生成课件的轻量大纲。\n"
            "严格要求：只输出一个 JSON 对象，不要任何 Markdown 标记、代码围栏、解释文字或思考过程。\n"
            "JSON 格式为：\n"
            '{"topic": "...", "audience": "...", "objective": "...", "duration_minutes": 45, '
            '"context_signals": {}, "sources": [], '
            '"plans": [{"title": "...", "layout": "title|bullets|two_column|callout|summary", '
            '"purpose": "...", "subtitle": "..."}]}\n'
            "plans 必须恰好包含 8 到 12 项；不得包含 bullets、notes、citations、media "
            "或完整讲稿，也不要生成页面 ID。\n"
            f"{mode_guidance}\n"
            "现在请直接输出 JSON："
        )
        return await self._run_stage(request, prompt, mode=mode)

    async def generate_slide_batch(
        self,
        request: AgentRequest,
        *,
        deck_context: dict[str, Any],
        plans: list[dict[str, Any]],
        mode: str = "react",
        correction: bool = False,
    ) -> StageCallResult:
        expected_ids = [str(plan["id"]) for plan in plans]
        correction_text = (
            "这是针对上一响应失败的纠正调用。严格补齐且只返回预期 ID。"
            if correction
            else ""
        )
        prompt = (
            "你正在生成课件中一个小批次的页面详情。只输出 JSON 对象，不要 Markdown。"
            f"预期 ID（必须各出现一次且不得增加其他 ID）：{json.dumps(expected_ids, ensure_ascii=False)}。"
            "格式为 {slides:[{id, layout, title, subtitle, bullets, notes, key_points, "
            "citations, media, columns}]}。保留来源引用并写出可直接授课的内容。"
            f"{correction_text}\n"
            f"课件元数据与来源：{json.dumps(deck_context, ensure_ascii=False)}\n"
            f"页面计划：{json.dumps(plans, ensure_ascii=False)}"
        )
        return await self._run_stage(request, prompt, mode=mode)

    async def identify_slide_defects(
        self,
        request: AgentRequest,
        *,
        deck_context: dict[str, Any],
        slides: list[dict[str, Any]],
    ) -> StageCallResult:
        compact_slides = [
            {
                "id": slide.get("id"),
                "title": slide.get("title"),
                "layout": slide.get("layout"),
                "bullets": slide.get("bullets"),
                "citations": slide.get("citations"),
            }
            for slide in slides
        ]
        prompt = (
            "对课件做一次紧凑缺陷检查。只输出 JSON 对象 {defective_ids:[str]}。"
            "仅列出确实需要重写的页面 ID，不得提出新页面或改动其他页面。\n"
            f"课件元数据：{json.dumps(deck_context, ensure_ascii=False)}\n"
            f"页面摘要：{json.dumps(compact_slides, ensure_ascii=False)}"
        )
        return await self._run_stage(request, prompt, mode="reflection")

    async def _run_stage(
        self, request: AgentRequest, system_prompt: str, *, mode: str
    ) -> StageCallResult:
        provider_snapshot = build_provider_snapshot(self._config)
        runtime = runtime_from_provider_snapshot(provider_snapshot)
        spec = AgentRunSpec(
            initial_messages=self._build_messages(request, system_prompt),
            tools=self._get_tools(),
            runtime=runtime,
            max_iterations=self._get_max_iterations(mode),
            max_tool_result_chars=self._config.agents.defaults.max_tool_result_chars,
            fail_on_tool_error=self._config.agents.defaults.fail_on_tool_error,
            workspace=self._config.workspace_path,
            context_block_limit=self._config.agents.defaults.context_block_limit,
            provider_retry_mode=self._config.agents.defaults.provider_retry_mode,
        )
        result = await AgentRunner().run(spec)
        return StageCallResult(
            text=result.final_content or "",
            stop_reason=getattr(result, "stop_reason", None),
        )

    def _build_system_prompt(self, request: AgentRequest, mode: str) -> str:
        """Build a system prompt that guides nanobot's execution mode."""
        base = (
            "你是教师端课程迭代助手的『幻灯生成』模式。"
            "请综合课程学情、课堂总结、批改反馈和联网检索的行业/岗位信息，"
            "严格输出符合下面 JSON schema 的对象（不能输出任何 Markdown 或解释）：\n"
        )

        schema = (
            "{\n"
            '  "topic": str, "audience": str, "objective": str, "duration_minutes": int,\n'
            '  "context_signals": {"learning_analysis": str, "weak_points": [str],'
            ' "classroom_summary": str, "grading": str, "job_skill_focus": [str],'
            ' "industry_updates": [{"title": str, "url": str, "snippet": str}]},\n'
            '  "slides": [{"index": int, "layout": "title|bullets|two_column|callout|summary",'
            ' "title": str, "subtitle": str, "bullets": [str], "notes": str,'
            ' "key_points": [str], "citations": [{"title": str, "url": str}],'
            ' "media": [{"kind": "image|video|gif|embed|animation", "url": str, "title": str,'
            ' "caption": str, "alt": str, "poster": str, "placement": "top|right|left|background|inline",'
            ' "autoplay": bool, "loop": bool, "muted": bool, "start_ms": int, "end_ms": int}]},\n'
            '  "sources": [{"title": str, "url": str, "snippet": str}]\n'
            "}\n"
            "layout 仅可取 title/bullets/two_column/callout/summary；"
            "当知识点更适合动态演示、情境播放、过程讲解时，可在 media 中增加 0~2 个素材建议，"
            "优先使用可直接打开的公开视频链接、动图或示意图，并说明其插入位置；"
            "至少有一页 citations 引用 industry_updates 中的条目；"
            "只输出 JSON 对象。"
        )

        # Mode-specific instructions
        mode_instructions = {
            "react": (
                "\n\n[执行模式：ReAct]\n"
                "请按以下步骤思考和行动：\n"
                "1. Thought: 分析主题和上下文，确定需要什么信息\n"
                "2. Action: 使用工具搜索行业案例和岗位技能\n"
                "3. Observation: 观察搜索结果，提取有价值的信息\n"
                "4. 重复以上步骤，直到收集到足够的信息\n"
                "5. 生成最终的 slide_deck JSON\n"
            ),
            "plan_and_solve": (
                "\n\n[执行模式：Plan-and-Solve]\n"
                "请先制定详细计划，再逐步执行：\n"
                "1. Plan: 分析主题，设计教学结构（导入→核心→案例→总结→练习），分配页数预算（至少 8 页）\n"
                "2. Solve: 逐页生成详细内容，确保每页有明确的教学功能\n"
                "3. Check: 检查是否满足页数要求和结构多样性\n"
                "4. 如果不满足，补充缺失的页面\n"
            ),
            "reflection": (
                "\n\n[执行模式：Reflection]\n"
                "请按以下步骤生成高质量课件：\n"
                "1. Generate: 生成第一版完整 slide_deck\n"
                "2. Critique: 自我评审，检查：\n"
                "   - 页数是否 >= 8？\n"
                "   - 是否有多样化 layout？\n"
                "   - 是否有案例/练习/总结部分？\n"
                "   - 是否有媒体建议？\n"
                "   - 是否有引用和行业信息？\n"
                "3. Revise: 根据评审意见补页/重写不足部分\n"
                "4. 再次评审，确保质量达标\n"
            ),
        }

        return base + schema + mode_instructions.get(mode, mode_instructions["react"])

    def _build_messages(
        self, request: AgentRequest, system_prompt: str
    ) -> list[dict[str, str]]:
        """Convert AgentRequest to nanobot message format."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Combine context and request into one user turn for OpenAI-compatible providers.
        context_parts: list[str] = []
        for artifact in request.context.selected_artifacts:
            if artifact.type in ("learning_analysis", "classroom_summary", "grading"):
                content = artifact.content
                if not content and artifact.data:
                    content = json.dumps(artifact.data, ensure_ascii=False)
                context_parts.append(f"[{artifact.type}] {content[:800]}")

        if request.previous_slide_deck is not None:
            context_parts.append(
                "[previous_slide_deck] "
                + json.dumps(request.previous_slide_deck, ensure_ascii=False)
            )

        user_parts = []
        if context_parts:
            user_parts.append("以下是课程上下文信息：\n" + "\n".join(context_parts))
        user_parts.append(request.content)
        messages.append({"role": "user", "content": "\n\n".join(user_parts)})

        return messages

    def _get_tools(self) -> ToolRegistry:
        """Build the tool registry for this run."""
        from app.agents.nanobot.tools.bing_search import BingSearchTool
        from app.agents.nanobot.tools.slide_validator import SlideDeckValidatorTool

        tools = ToolRegistry()
        if self._bing_provider is not None and self._bing_provider.is_configured:
            tools.register(BingSearchTool(self._bing_provider))
        tools.register(SlideDeckValidatorTool())
        return tools

    def _get_max_iterations(self, mode: str) -> int:
        """Get max iterations for the given mode."""
        limits = {
            "react": 20,
            "plan_and_solve": 10,
            "reflection": 6,
        }
        return limits.get(mode, 20)

    def _to_agent_result(
        self, nanobot_result: Any, request: AgentRequest
    ) -> AgentResult:
        """Convert nanobot's output to AgentResult."""
        text = nanobot_result.final_content or ""

        structured_data = None
        try:
            structured_data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Create artifact if we have structured data
        artifact = None
        if structured_data and "slides" in structured_data:
            artifact = AgentArtifact(
                type="slide_deck",
                title=structured_data.get("topic", request.content[:60]),
                content=text,
                data=structured_data,
                format="json",
            )

        warnings = (nanobot_result.error,) if nanobot_result.error else ()
        return AgentResult(
            text=text,
            structured_data=structured_data,
            artifact=artifact,
            citations=request.context.sources,
            warnings=warnings,
        )
