"""Course iteration executor with a slide_deck generation branch."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from app.agents.contracts import (
    AgentArtifact,
    AgentContext,
    AgentRequest,
    AgentResult,
    ContextArtifact,
)
from app.agents.executors.generic_chat import GenericChatExecutor
from app.artifacts.repositories import ArtifactRepository
from app.core.errors import AppError
from app.integrations.llm.providers import ChatProvider
from app.integrations.search.bing import BingSearchProvider, SearchResult
from app.skills.slide_deck_json import SlideDeckJsonSkill
from app.skills.slide_deck_markdown import SlideDeckMarkdownSkill
from app.skills.pptx_templates.catalog import (
    DEFAULT_TEMPLATE_ID,
    find_explicit_template_id,
    is_known_template_id,
    prompt_template_catalog,
    template_metadata,
)

SLIDE_DECK_KEYWORDS: tuple[str, ...] = (
    "课件",
    "幻灯",
    "slide",
    "ppt",
    "PPT",
    "演示文稿",
)

_SLIDE_DECK_SYSTEM = (
    "你是教师端课程迭代助手的『幻灯生成』模式。"
    "请综合课程学情、课堂总结、批改反馈和联网检索的行业/岗位信息，"
    "严格输出符合下面 JSON schema 的对象（不能输出任何 Markdown 或解释）：\n"
    "{\n"
    '  "topic": str, "audience": str, "objective": str, "duration_minutes": int,\n'
    '  "template_id": "ai_tech|business_plan",\n'
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
    "template_id 只能从上下文提供的 template_catalog 中选择；"
    "如果 forced_template_id 非空，必须原样返回该值；"
    "layout 仅可取 title/bullets/two_column/callout/summary；"
    "当知识点更适合动态演示、情境播放、过程讲解时，可在 media 中增加 0~2 个素材建议，"
    "优先使用可直接打开的公开视频链接、动图或示意图，并说明其插入位置；"
    "至少有一页 citations 引用 industry_updates 中的条目；"
    "只输出 JSON 对象。"
)


ArtifactRepositoryFactory = Callable[[], ArtifactRepository | None]


class CourseIterationExecutor:
    def __init__(
        self,
        chat_provider: ChatProvider,
        bing_provider: BingSearchProvider | None,
        artifact_repository_factory: ArtifactRepositoryFactory | None,
    ) -> None:
        self.chat_provider = chat_provider
        self.bing_provider = bing_provider
        self.artifact_repository_factory = artifact_repository_factory
        self._json_skill = SlideDeckJsonSkill()
        self._markdown_skill = SlideDeckMarkdownSkill()

    async def execute(self, request: AgentRequest) -> AgentResult:
        if not _should_generate_slide_deck(request.content):
            fallback = GenericChatExecutor(self.chat_provider)
            result = await fallback.execute(request)
            topic = _infer_topic(request.content)
            data = {
                "topic": topic,
                "mode": "course_iteration",
            }
            return AgentResult(
                text=result.text,
                structured_data=data,
                citations=result.citations,
                artifact=AgentArtifact(
                    type="course_iteration",
                    title=topic,
                    content=result.text,
                    data=data,
                    format="markdown",
                ),
                warnings=result.warnings,
            )
        return await self._generate_slide_deck(request)

    async def _generate_slide_deck(self, request: AgentRequest) -> AgentResult:
        if not self.chat_provider.is_configured:
            raise RuntimeError("chat_model_unconfigured")

        topic = _infer_topic(request.content)
        course_signals = _collect_course_signals(request.context)
        previous_deck = self._load_previous_deck(request)
        explicit_template_id = find_explicit_template_id(request.content)
        previous_template_id = _previous_template_id(previous_deck)
        forced_template_id = explicit_template_id or previous_template_id

        warnings: list[str] = []
        industry_result, job_result = await self._run_bing_searches(topic)
        if self.bing_provider is None or not self.bing_provider.is_configured:
            warnings.append("联网检索未启用（未配置 BING_SEARCH_API_KEY）")
        elif not industry_result.available and not job_result.available:
            warnings.append("联网检索暂时不可用，本次结果为空")

        prompt_payload = {
            "topic": topic,
            "user_request": request.content,
            "course_signals": course_signals,
            "industry_updates": [_search_item_to_dict(item) for item in industry_result.items],
            "job_skill_hits": [_search_item_to_dict(item) for item in job_result.items],
            "previous_deck": previous_deck,
            "template_catalog": prompt_template_catalog(),
            "forced_template_id": forced_template_id,
        }
        base_messages: list[dict[str, str]] = [
            {"role": "system", "content": _SLIDE_DECK_SYSTEM},
            {
                "role": "user",
                "content": (
                    "以下是本次生成幻灯所需的上下文 JSON，请据此生成课件：\n"
                    + json.dumps(prompt_payload, ensure_ascii=False)
                ),
            },
        ]

        raw = await _collect_stream(
            self.chat_provider.stream_reply(
                base_messages,
                response_format={"type": "json_object"},
            )
        )
        data: dict[str, Any] | None = None
        try:
            data = self._json_skill.run(_extract_json(raw))
        except AppError:
            repair_messages = base_messages + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        "你上一次输出不是合法 JSON。请只输出一个符合 schema 的 JSON 对象，"
                        "不要输出 Markdown 或多余文本。"
                    ),
                },
            ]
            raw = await _collect_stream(
                self.chat_provider.stream_reply(
                    repair_messages,
                    response_format={"type": "json_object"},
                )
            )
            data = self._json_skill.run(_extract_json(raw))

        if explicit_template_id:
            selected_template_id = explicit_template_id
            selection_source = "explicit"
        elif previous_template_id:
            selected_template_id = previous_template_id
            selection_source = "previous"
        elif is_known_template_id(data.get("template_id")):
            selected_template_id = str(data["template_id"])
            selection_source = "llm"
        else:
            selected_template_id = DEFAULT_TEMPLATE_ID
            selection_source = "fallback"
        data.update(template_metadata(selected_template_id, selection_source))

        # Enrich the sanitised structure with anything the model did not carry over.
        signals = data.setdefault("context_signals", {})
        if not signals.get("industry_updates"):
            signals["industry_updates"] = [
                _search_item_to_dict(item) for item in industry_result.items
            ]
        if not signals.get("job_skill_focus") and job_result.items:
            signals["job_skill_focus"] = [
                f"{item.title}: {item.snippet}".strip(": ") for item in job_result.items
            ]
        if not data.get("sources"):
            merged = [_search_item_to_dict(item) for item in industry_result.items]
            merged.extend(_search_item_to_dict(item) for item in job_result.items)
            data["sources"] = merged

        markdown = self._markdown_skill.run(data)
        artifact = AgentArtifact(
            type="slide_deck",
            title=data.get("topic") or topic,
            content=markdown,
            data=data,
            format="json",
        )
        return AgentResult(
            text=markdown,
            structured_data=data,
            citations=request.context.sources,
            artifact=artifact,
            warnings=tuple(warnings),
        )

    async def _run_bing_searches(self, topic: str) -> tuple[SearchResult, SearchResult]:
        if self.bing_provider is None or not self.bing_provider.is_configured:
            empty = SearchResult(available=False, items=())
            return empty, empty
        queries = (
            f"{topic} 最新应用 案例 2025",
            f"{topic} 岗位 技能 招聘 应届生",
        )
        results = await asyncio.gather(
            self.bing_provider.search(queries[0]),
            self.bing_provider.search(queries[1]),
            return_exceptions=True,
        )
        cleaned: list[SearchResult] = []
        for entry in results:
            if isinstance(entry, SearchResult):
                cleaned.append(entry)
            else:
                cleaned.append(SearchResult(available=False, items=()))
        return cleaned[0], cleaned[1]

    def _load_previous_deck(self, request: AgentRequest) -> dict[str, Any] | None:
        if self.artifact_repository_factory is None:
            return None
        try:
            repository = self.artifact_repository_factory()
        except Exception:  # noqa: BLE001
            return None
        if repository is None:
            return None
        try:
            latest = repository.latest_by_conversation(
                request.workspace_id, request.conversation_id, "slide_deck"
            )
        except Exception:  # noqa: BLE001
            return None
        if latest is None:
            return None
        return {
            "topic": latest.title,
            "data": latest.data,
        }


def _should_generate_slide_deck(content: str) -> bool:
    lowered = (content or "").lower()
    for keyword in SLIDE_DECK_KEYWORDS:
        if keyword.lower() in lowered:
            return True
    return False


def _infer_topic(content: str) -> str:
    text = (content or "").strip()
    if not text:
        return "课件"
    # Prefer content between 「」 or 《》 or quotes.
    for opener, closer in (("「", "」"), ("《", "》"), ("『", "』"), ('"', '"'), ('"', '"')):
        if opener in text and closer in text:
            start = text.index(opener) + 1
            end = text.index(closer, start)
            if end > start:
                return text[start:end].strip() or text[:40]
    return text[:60]


def _collect_course_signals(context: AgentContext) -> dict[str, Any]:
    signals: dict[str, Any] = {
        "learning_analysis": "",
        "classroom_summary": "",
        "grading": "",
    }
    for artifact in context.selected_artifacts:
        summary = _summarise_artifact(artifact)
        if artifact.type == "learning_analysis" and not signals["learning_analysis"]:
            signals["learning_analysis"] = summary
        elif artifact.type == "classroom_summary" and not signals["classroom_summary"]:
            signals["classroom_summary"] = summary
        elif artifact.type == "grading" and not signals["grading"]:
            signals["grading"] = summary
    return signals


def _summarise_artifact(artifact: ContextArtifact) -> str:
    text = artifact.content or ""
    if not text and artifact.data:
        try:
            text = json.dumps(artifact.data, ensure_ascii=False)
        except (TypeError, ValueError):
            text = ""
    text = text.strip()
    if len(text) > 800:
        text = text[:800] + "…"
    return text


def _search_item_to_dict(item) -> dict[str, str]:
    return {"title": item.title, "url": item.url, "snippet": item.snippet}


def _previous_template_id(previous_deck: dict[str, Any] | None) -> str | None:
    if not previous_deck:
        return None
    previous_data = previous_deck.get("data")
    if not isinstance(previous_data, dict):
        return None
    template_id = previous_data.get("template_id")
    return str(template_id) if is_known_template_id(template_id) else None


async def _collect_stream(iterator) -> str:
    chunks: list[str] = []
    async for delta in iterator:
        chunks.append(delta)
    return "".join(chunks)


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def _extract_json(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return stripped
    match = _JSON_FENCE.search(stripped)
    if match:
        return match.group(1).strip()
    return stripped
