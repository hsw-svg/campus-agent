"""Build and validate the post-class summary from explicitly selected artifacts."""

from __future__ import annotations

import json
from typing import Any, Iterable

from app.agents.contracts import ContextArtifact
from app.core.errors import AppError


_ACTIVITY_TYPES = {"classroom_activity", "classroom_activity_package", "activity_package"}
_OBSERVATION_TYPES = {"classroom_observation", "classroom_observation_analysis"}


class ClassroomSummarySkill:
    id = "classroom_summary"
    version = "1"
    input_type = "selected classroom artifacts"
    output_type = "ClassroomSummary"
    error_codes = (
        "classroom_summary_input_incomplete",
        "classroom_summary_input_invalid",
        "classroom_summary_output_invalid",
    )
    has_side_effects = False
    can_access_workspace = False

    def select_inputs(
        self, artifacts: Iterable[ContextArtifact]
    ) -> tuple[ContextArtifact, ContextArtifact]:
        selected = tuple(artifacts)
        activity = next((item for item in selected if item.type in _ACTIVITY_TYPES), None)
        observation = next((item for item in selected if item.type in _OBSERVATION_TYPES), None)
        missing = []
        if activity is None:
            missing.append("课堂互动活动包")
        if observation is None:
            missing.append("课堂观察记录")
        if missing:
            raise AppError(
                code="classroom_summary_input_incomplete",
                message="请选择课堂互动活动包和课堂观察记录后再生成总结。",
                status_code=422,
                details={"missing_inputs": missing},
            )
        if observation.data.get("status") == "needs_confirmation":
            raise AppError(
                code="classroom_summary_input_invalid",
                message="课堂观察仍待确认，确认统计归属后才能生成课后总结。",
                status_code=422,
                details={"ambiguities": observation.data.get("ambiguities", [])},
            )
        return activity, observation

    def prompt(self, artifacts: Iterable[ContextArtifact]) -> str:
        activity, observation = self.select_inputs(artifacts)
        payload = {
            "activity_package": activity.data,
            "classroom_observation": observation.data,
        }
        return (
            "你是教师课后总结助手。只能根据下列已明确选择的活动包和课堂观察生成总结，"
            "不能补造人数、比例、学生个体信息或未选择的资料。只输出合法 JSON，不要 Markdown。"
            "JSON 必须包含 classroom_summary、common_misconceptions、teaching_reflection、"
            "follow_up_practice、next_lesson_adjustments 五个字段；其中误区、后续练习和下次调整项为数组。\n"
            + json.dumps(payload, ensure_ascii=False)
        )

    def parse(self, raw: str, artifacts: Iterable[ContextArtifact]) -> dict[str, Any]:
        self.select_inputs(artifacts)
        try:
            payload = json.loads(_strip_json_fence(raw))
        except (TypeError, json.JSONDecodeError) as error:
            raise AppError(
                code="classroom_summary_output_invalid",
                message="模型返回的课后总结不是合法 JSON。",
                status_code=422,
                details={"reason": str(error)},
            ) from error
        if not isinstance(payload, dict):
            raise AppError(
                code="classroom_summary_output_invalid",
                message="课后总结必须是 JSON 对象。",
                status_code=422,
            )

        result = {
            "scope": "class",
            "classroom_summary": _required_text(payload, "classroom_summary", "课堂摘要"),
            "common_misconceptions": _required_list(payload, "common_misconceptions", "共同误区"),
            "teaching_reflection": _required_text(
                payload, "teaching_reflection", "教学策略反思", fallback_key="教学反思"
            ),
            "follow_up_practice": _required_list(payload, "follow_up_practice", "后续练习"),
            "next_lesson_adjustments": _required_list(payload, "next_lesson_adjustments", "下次课调整项"),
        }
        return result

    def markdown(self, data: dict[str, Any]) -> str:
        lines = [
            "# 课后课堂总结",
            "",
            "## 课堂摘要",
            data["classroom_summary"],
            "",
            "## 共同误区",
            *_bullets(data["common_misconceptions"]),
            "",
            "## 教学策略反思",
            data["teaching_reflection"],
            "",
            "## 后续练习",
            *_bullets(data["follow_up_practice"]),
            "",
            "## 下次课调整项",
            *_bullets(data["next_lesson_adjustments"]),
        ]
        return "\n".join(lines)


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return text


def _required_text(payload: dict[str, Any], key: str, chinese_key: str, fallback_key: str | None = None) -> str:
    value = payload.get(key)
    if value is None:
        value = payload.get(chinese_key)
    if value is None and fallback_key:
        value = payload.get(fallback_key)
    text = str(value).strip() if value is not None else ""
    if not text:
        raise AppError(
            code="classroom_summary_output_invalid",
            message=f"课后总结缺少 {chinese_key}。",
            status_code=422,
        )
    return text


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, dict):
            item = item.get("text") or item.get("content") or item.get("action")
        text = str(item).strip() if item is not None else ""
        if text:
            result.append(text)
    return result


def _required_list(payload: dict[str, Any], key: str, chinese_key: str) -> list[str]:
    if key in payload:
        value = payload[key]
    elif chinese_key in payload:
        value = payload[chinese_key]
    else:
        raise AppError(
            code="classroom_summary_output_invalid",
            message=f"课后总结缺少 {chinese_key}。",
            status_code=422,
        )
    if not isinstance(value, list):
        raise AppError(
            code="classroom_summary_output_invalid",
            message=f"课后总结的 {chinese_key} 必须是数组。",
            status_code=422,
        )
    return _text_list(value)


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- 暂无"]
