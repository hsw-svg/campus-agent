"""Course iteration executor v2 — uses nanobot runner for enhanced PPT generation.

This version delegates to nanobot's agent runner for ReAct/Plan-and-Solve/Reflection
execution modes, resulting in higher quality slide decks with more pages and richer content.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.agents.contracts import (
    AgentArtifact,
    AgentRequest,
    AgentResult,
)
from app.agents.executors.generic_chat import GenericChatExecutor
from app.agents.nanobot.runner import NanobotRunner
from app.artifacts.repositories import ArtifactRepository
from app.core.errors import AppError
from app.integrations.llm.providers import ChatProvider
from app.skills.slide_deck_json import SlideDeckJsonSkill
from app.skills.slide_deck_markdown import SlideDeckMarkdownSkill

SLIDE_DECK_KEYWORDS: tuple[str, ...] = (
    "课件",
    "幻灯",
    "slide",
    "ppt",
    "PPT",
    "演示文稿",
)

# Mode selection keywords
_PLAN_KEYWORDS = ("规划", "计划", "结构", "大纲", "设计", "安排")
_REFLECTION_KEYWORDS = ("详细", "优质", "高质量", "精品", "完善", "深入")


ArtifactRepositoryFactory = Callable[[], ArtifactRepository | None]


class CourseIterationExecutorV2:
    """Course iteration executor using nanobot runner for enhanced PPT generation.

    This executor delegates to nanobot's agent runner for multi-step execution,
    resulting in higher quality slide decks with more pages and richer content.
    """

    def __init__(
        self,
        chat_provider: ChatProvider,
        nanobot_runner: NanobotRunner,
        artifact_repository_factory: ArtifactRepositoryFactory | None,
    ) -> None:
        self.chat_provider = chat_provider
        self.nanobot_runner = nanobot_runner
        self.artifact_repository_factory = artifact_repository_factory
        self._json_skill = SlideDeckJsonSkill()
        self._markdown_skill = SlideDeckMarkdownSkill()

    async def execute(self, request: AgentRequest) -> AgentResult:
        if not _should_generate_slide_deck(request.content):
            fallback = GenericChatExecutor(self.chat_provider)
            return await fallback.execute(request)
        return await self._generate_slide_deck(request)

    async def _generate_slide_deck(self, request: AgentRequest) -> AgentResult:
        if not self.chat_provider.is_configured:
            raise RuntimeError("chat_model_unconfigured")

        mode = _select_mode(request.content)
        staged_request = self._with_previous_deck(request)
        data = await self._generate_staged_deck(staged_request, mode)
        return self._build_slide_deck_result(data, request)

    async def _generate_staged_deck(
        self, request: AgentRequest, mode: str
    ) -> dict[str, Any]:
        # Try outline generation with one retry on parse failure
        outline = None
        for attempt in range(2):
            outline_call = await self.nanobot_runner.generate_slide_outline(
                request, mode=mode
            )
            try:
                outline = _parse_object(outline_call.text, "outline")
                break
            except AppError:
                if attempt == 1:
                    raise  # Second attempt also failed, propagate error
                continue  # Retry once

        raw_plans = outline.get("plans")
        if not isinstance(raw_plans, list) or not 8 <= len(raw_plans) <= 12:
            raise _stage_error("Outline must contain between 8 and 12 slide plans.")

        plans: list[dict[str, Any]] = []
        for index, raw_plan in enumerate(raw_plans, start=1):
            if not isinstance(raw_plan, dict):
                raise _stage_error("Each outline plan must be an object.")
            if any(key in raw_plan for key in ("bullets", "notes", "citations", "media")):
                raise _stage_error("Outline plans must remain compact.")
            plans.append({**raw_plan, "id": f"slide-{index:03d}", "index": index})

        deck_context = {key: value for key, value in outline.items() if key != "plans"}
        # Preserve request-owned context even when a model omits it from the outline.
        if request.previous_slide_deck is not None:
            deck_context["previous_slide_deck"] = request.previous_slide_deck
        if request.context.sources:
            deck_context["request_sources"] = [
                {
                    "title": source.filename,
                    "excerpt": source.excerpt,
                    "position": source.page_number,
                }
                for source in request.context.sources
            ]

        merged: dict[str, dict[str, Any]] = {}
        for offset in range(0, len(plans), 2):
            batch_plans = plans[offset : offset + 2]
            for slide in await self._generate_batch_with_recovery(
                request, deck_context, batch_plans, mode
            ):
                merged[slide["id"]] = slide

        ordered = [merged[plan["id"]] for plan in plans]
        if mode == "reflection":
            ordered = await self._reflect_once(
                request, deck_context, plans, ordered, mode
            )

        sources = list(deck_context.get("sources") or [])
        sources.extend(
            {
                "title": source.get("title", ""),
                "url": "",
                "snippet": source.get("excerpt", ""),
            }
            for source in deck_context.get("request_sources") or []
            if isinstance(source, dict)
        )
        payload = {
            **deck_context,
            "slides": ordered,
            "sources": sources,
        }
        return self._json_skill.run(payload)

    async def _generate_batch_with_recovery(
        self,
        request: AgentRequest,
        deck_context: dict[str, Any],
        plans: list[dict[str, Any]],
        mode: str,
    ) -> list[dict[str, Any]]:
        for correction in (False, True):
            call = await self.nanobot_runner.generate_slide_batch(
                request,
                deck_context=deck_context,
                plans=plans,
                mode=mode,
                correction=correction,
            )
            slides = _validated_stage_slides(call.text, plans)
            if slides is not None and not _is_length_stop(call.stop_reason):
                return slides

        recovered: list[dict[str, Any]] = []
        for plan in plans:
            slide = None
            # A split page gets one initial attempt and one correction attempt.
            for correction in (False, True):
                call = await self.nanobot_runner.generate_slide_batch(
                    request,
                    deck_context=deck_context,
                    plans=[plan],
                    mode=mode,
                    correction=correction,
                )
                candidate = _validated_stage_slides(call.text, [plan])
                if candidate is not None and not _is_length_stop(call.stop_reason):
                    slide = candidate[0]
                    break
            if slide is None:
                raise _stage_error(f"Unable to generate slide '{plan['id']}'.")
            recovered.append(slide)
        return recovered

    async def _reflect_once(
        self,
        request: AgentRequest,
        deck_context: dict[str, Any],
        plans: list[dict[str, Any]],
        slides: list[dict[str, Any]],
        mode: str,
    ) -> list[dict[str, Any]]:
        call = await self.nanobot_runner.identify_slide_defects(
            request, deck_context=deck_context, slides=slides
        )
        defects = _parse_object(call.text, "reflection").get("defective_ids", [])
        known_ids = {plan["id"] for plan in plans}
        if not isinstance(defects, list) or len(defects) != len(set(defects)):
            raise _stage_error("Reflection returned invalid or duplicate slide IDs.")
        if any(not isinstance(item, str) or item not in known_ids for item in defects):
            raise _stage_error("Reflection returned an unknown slide ID.")

        replacements: dict[str, dict[str, Any]] = {}
        plan_by_id = {plan["id"]: plan for plan in plans}
        for slide_id in defects:
            call = await self.nanobot_runner.generate_slide_batch(
                request,
                deck_context={**deck_context, "defect_regeneration": True},
                plans=[plan_by_id[slide_id]],
                mode=mode,
                correction=True,
            )
            candidate = _validated_stage_slides(call.text, [plan_by_id[slide_id]])
            if candidate is None or _is_length_stop(call.stop_reason):
                raise _stage_error(f"Unable to regenerate defective slide '{slide_id}'.")
            replacements[slide_id] = candidate[0]
        return [replacements.get(slide["id"], slide) for slide in slides]

    def _build_slide_deck_result(
        self, data: dict[str, Any], request: AgentRequest
    ) -> AgentResult:
        markdown = self._markdown_skill.run(data)
        artifact = AgentArtifact(
            type="slide_deck",
            title=data.get("topic") or request.content[:60],
            content=markdown,
            data=data,
            format="json",
        )
        return AgentResult(
            text=markdown,
            structured_data=data,
            artifact=artifact,
            citations=request.context.sources,
        )

    def _ensure_valid_slide_deck(
        self, result: AgentResult, request: AgentRequest
    ) -> AgentResult:
        """Normalize nanobot output before exposing the stable artifact contract."""
        payload = (
            result.artifact.data
            if result.artifact is not None and result.artifact.type == "slide_deck"
            else _extract_json(result.text)
        )
        data = self._json_skill.run(payload)

        markdown = self._markdown_skill.run(data)
        artifact = AgentArtifact(
            type="slide_deck",
            title=data.get("topic") or request.content[:60],
            content=markdown,
            data=data,
            format="json",
        )

        return AgentResult(
            text=markdown,
            structured_data=data,
            artifact=artifact,
            citations=result.citations,
            warnings=result.warnings,
        )

    def _with_previous_deck(self, request: AgentRequest) -> AgentRequest:
        previous_deck = self._load_previous_deck(request)
        if previous_deck is None:
            return request
        return AgentRequest(
            workspace_id=request.workspace_id,
            conversation_id=request.conversation_id,
            role=request.role,
            agent_id=request.agent_id,
            content=request.content,
            selected_attachment_ids=request.selected_attachment_ids,
            selected_artifact_ids=request.selected_artifact_ids,
            course_id=request.course_id,
            workflow_id=request.workflow_id,
            parent_run_id=request.parent_run_id,
            input_refs=request.input_refs,
            context=request.context,
            previous_slide_deck=previous_deck,
        )

    def _load_previous_deck(self, request: AgentRequest) -> dict | None:
        if self.artifact_repository_factory is None:
            return None
        try:
            repository = self.artifact_repository_factory()
            if repository is None:
                return None
            latest = repository.latest_by_conversation(
                request.workspace_id, request.conversation_id, "slide_deck"
            )
        except Exception:  # noqa: BLE001 - previous context is optional
            return None
        if latest is None:
            return None
        return {"topic": latest.title, "data": latest.data}


def _should_generate_slide_deck(content: str) -> bool:
    lowered = (content or "").lower()
    for keyword in SLIDE_DECK_KEYWORDS:
        if keyword.lower() in lowered:
            return True
    return False


def _select_mode(content: str) -> str:
    """Select execution mode based on content keywords."""
    lowered = (content or "").lower()

    # Check for reflection keywords (high quality requests)
    for keyword in _REFLECTION_KEYWORDS:
        if keyword in lowered:
            return "reflection"

    # Check for plan keywords
    for keyword in _PLAN_KEYWORDS:
        if keyword in lowered:
            return "plan_and_solve"

    # Default to react mode
    return "react"


def _extract_json(text: str) -> str:
    """Extract JSON from text, handling code fences."""
    import re

    stripped = (text or "").strip()
    if not stripped:
        return stripped

    json_fence = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
    match = json_fence.search(stripped)
    if match:
        return match.group(1).strip()

    json_match = re.search(r"\{[\s\S]*\}", stripped)
    if json_match:
        return json_match.group()

    return stripped


def _stage_error(message: str) -> AppError:
    return AppError(
        code="slide_deck_stage_invalid",
        message=message,
        status_code=422,
    )


def _parse_object(text: str, stage: str) -> dict[str, Any]:
    extracted = _extract_json(text)
    try:
        value = json.loads(extracted)
    except (json.JSONDecodeError, TypeError) as error:
        # Include a truncated excerpt of the actual response for debugging
        excerpt = (text or "")[:500]
        raise _stage_error(
            f"The {stage} stage did not return valid JSON. "
            f"Response excerpt: {excerpt}"
        ) from error
    if not isinstance(value, dict):
        raise _stage_error(f"The {stage} stage must return a JSON object.")
    return value


def _validated_stage_slides(
    text: str, plans: list[dict[str, Any]]
) -> list[dict[str, Any]] | None:
    try:
        payload = _parse_object(text, "slide detail")
    except AppError:
        return None
    slides = payload.get("slides")
    if not isinstance(slides, list) or not all(isinstance(item, dict) for item in slides):
        return None
    expected_ids = [str(plan["id"]) for plan in plans]
    actual_ids = [str(slide.get("id") or "") for slide in slides]
    if actual_ids != expected_ids or len(actual_ids) != len(set(actual_ids)):
        return None
    plan_by_id = {str(plan["id"]): plan for plan in plans}
    return [
        {
            **slide,
            "id": slide_id,
            "index": plan_by_id[slide_id]["index"],
        }
        for slide, slide_id in zip(slides, actual_ids, strict=True)
    ]


def _is_length_stop(stop_reason: str | None) -> bool:
    if not stop_reason:
        return False
    normalized = stop_reason.lower().replace("-", "_")
    return any(marker in normalized for marker in ("length", "max_token", "truncat"))
