"""Validate and serialize teacher classroom activity packages.

The model is allowed to suggest activities, but the package that reaches the
API is always normalized and checked here.  This keeps timing and answer
correctness deterministic and lets a partially valid response remain useful.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.errors import AppError


_TYPE_ALIASES = {
    "诊断题": "diagnostic",
    "诊断": "diagnostic",
    "选择题": "multiple_choice",
    "选择": "multiple_choice",
    "判断题": "true_false",
    "判断": "true_false",
    "讨论题": "discussion",
    "讨论": "discussion",
    "开放题": "discussion",
    "案例任务": "case",
    "案例": "case",
    "任务": "case",
    "multiple choice": "multiple_choice",
    "true false": "true_false",
    "true/false": "true_false",
    "open": "discussion",
    "question": "discussion",
}
_ALLOWED_TYPES = {"diagnostic", "multiple_choice", "true_false", "discussion", "case"}
_MINUTES_RE = re.compile(r"(?P<minutes>\d+(?:\.\d+)?)")


class ClassroomActivityPackageSkill:
    id = "classroom_activity_package"
    version = "1"
    input_type = "tuple[raw_json, max_duration_minutes]"
    output_type = "ClassroomActivityPackage"
    error_codes = ("classroom_activity_input_invalid", "classroom_activity_output_invalid")
    has_side_effects = False
    can_access_workspace = False

    def run(self, value: tuple[str, int]) -> dict[str, Any]:
        raw, maximum = _unpack(value)
        if maximum <= 0:
            raise AppError(
                code="classroom_activity_input_invalid",
                message="课堂活动总时长必须是正整数分钟。",
                status_code=422,
            )
        payload = _decode(raw)
        if isinstance(payload, list):
            payload = {"activities": payload}
        if not isinstance(payload, dict):
            raise _invalid_output("活动包必须是 JSON 对象。")

        source_activities = payload.get("activities", payload.get("items", []))
        if not isinstance(source_activities, list):
            raise _invalid_output("活动包的 activities 必须是数组。")

        valid: list[dict[str, Any]] = []
        discarded: list[dict[str, Any]] = []
        for index, source in enumerate(source_activities):
            try:
                activity = _normalize_activity(source, index)
            except ValueError as error:
                discarded.append({"index": index, "reason": str(error)})
                continue
            if sum(item["duration_minutes"] for item in valid) + activity["duration_minutes"] > maximum:
                discarded.append(
                    {
                        "index": index,
                        "reason": f"加入该活动后总时长会超过 {maximum} 分钟。",
                    }
                )
                continue
            valid.append(activity)

        if not valid:
            detail = "未找到可保留的合法课堂活动。"
            if discarded:
                detail += "；".join(item["reason"] for item in discarded)
            raise _invalid_output(detail, discarded)

        total_minutes = sum(item["duration_minutes"] for item in valid)
        errors = [item["reason"] for item in discarded]
        data = {
            "scope": "class",
            "topic": _text(payload.get("topic") or payload.get("theme")) or "课堂互动",
            "objectives": _text_list(payload.get("objectives") or payload.get("goals")),
            "duration_minutes": maximum,
            "total_minutes": total_minutes,
            "activities": valid,
            "discarded_items": discarded,
            "validation": {
                "valid": True,
                "partial": bool(discarded),
                "errors": errors,
            },
        }
        return {"data": data, "markdown": _to_markdown(data), "warnings": tuple(errors)}


def _unpack(value: tuple[str, int]) -> tuple[str, int]:
    if len(value) != 2:
        raise _invalid_output("活动包校验参数不完整。")
    raw, maximum = value
    if not isinstance(raw, str) or not raw.strip():
        raise _invalid_output("模型没有返回活动包内容。")
    try:
        normalized_maximum = int(maximum)
    except (TypeError, ValueError) as error:
        raise AppError(
            code="classroom_activity_input_invalid",
            message="课堂活动总时长必须是正整数分钟。",
            status_code=422,
        ) from error
    return raw, normalized_maximum


def _decode(raw: str) -> Any:
    candidate = raw.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as error:
        raise _invalid_output("模型返回的活动包不是合法 JSON。", {"reason": str(error)}) from error


def _normalize_activity(source: Any, index: int) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise ValueError("活动必须是对象。")
    kind = _canonical_type(source.get("type") or source.get("kind") or source.get("question_type"))
    if kind is None:
        raise ValueError("题型必须是诊断题、选择题、判断题、讨论题或案例任务。")
    prompt = _text(source.get("prompt") or source.get("question") or source.get("content") or source.get("task"))
    if not prompt:
        raise ValueError("活动缺少题目内容。")
    minutes = _positive_minutes(
        source.get("duration_minutes")
        or source.get("estimated_minutes")
        or source.get("minutes")
        or source.get("duration")
    )
    if minutes is None:
        raise ValueError("活动预计用时必须是正数。")

    options = _normalize_options(source.get("options") or source.get("choices"))
    answer = source.get("answer", source.get("correct_answer", source.get("reference_answer")))
    if kind == "multiple_choice":
        if len(options) < 2:
            raise ValueError("选择题至少需要两个不同选项。")
        labels = [_option_label(option) for option in options]
        if len(labels) != len(set(labels)):
            raise ValueError("选择题的选项标签必须唯一。")
        answer = _normalize_choice_answer(answer, options)
        if answer is None:
            raise ValueError("选择题必须有唯一且存在于选项中的答案。")
    elif kind == "true_false":
        answer = _normalize_boolean_answer(answer)
        if answer is None:
            raise ValueError("判断题必须有明确的正确或错误答案。")
    else:
        answer = _text(answer)

    rubric = _normalize_rubric(source.get("rubric") or source.get("scoring_rubric") or source.get("scoring_points"))
    if kind in {"diagnostic", "discussion", "case"} and not rubric:
        raise ValueError("开放性活动必须包含评分要点。")

    return {
        "id": _text(source.get("id")) or f"activity-{index + 1}",
        "title": _text(source.get("title") or source.get("name")) or f"课堂活动 {index + 1}",
        "type": kind,
        "duration_minutes": minutes,
        "objective": _text(source.get("objective") or source.get("goal")),
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "explanation": _text(source.get("explanation") or source.get("analysis")),
        "common_misconceptions": _text_list(
            source.get("common_misconceptions") or source.get("misconceptions") or source.get("common_errors")
        ),
        "teacher_prompt": _text(source.get("teacher_prompt") or source.get("teacher_hint")),
        "differentiated_hints": _normalize_hints(
            source.get("differentiated_hints") or source.get("hints")
        ),
        "rubric": rubric,
        "branches": _normalize_branches(source.get("branches") or source.get("branch_actions")),
    }


def _canonical_type(value: Any) -> str | None:
    text = _text(value).lower().replace("_", " ").replace("-", " ")
    if text in _ALLOWED_TYPES:
        return text
    return _TYPE_ALIASES.get(text)


def _positive_minutes(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    match = _MINUTES_RE.search(str(value))
    if match is None:
        return None
    number = float(match.group("minutes"))
    return int(number) if number.is_integer() and number > 0 else None


def _normalize_options(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [f"{key}. {_text(item)}" for key, item in value.items()]
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, dict):
            label = _text(item.get("label") or item.get("id"))
            text = _text(item.get("text") or item.get("content") or item.get("value"))
            result.append(f"{label}. {text}" if label and text else label or text)
        else:
            text = _text(item)
            if text:
                result.append(text)
    return list(dict.fromkeys(result))


def _normalize_choice_answer(value: Any, options: list[str]) -> str | None:
    if isinstance(value, list):
        if len(value) != 1:
            return None
        value = value[0]
    answer = _text(value)
    if not answer:
        return None
    labels = {_option_label(option) for option in options}
    if answer.upper() in labels:
        return answer.upper()
    if answer in options:
        return answer
    match = re.match(r"^([A-Za-z])(?:[.、:：)]|\s)", answer)
    if match and match.group(1).upper() in labels:
        return match.group(1).upper()
    return None


def _option_label(option: str) -> str:
    match = re.match(r"^\s*([A-Za-z])(?:[.、:：)]|\s|$)", option)
    return match.group(1).upper() if match else option.strip().upper()


def _normalize_boolean_answer(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    answer = _text(value).lower()
    if answer in {"true", "正确", "对", "是", "yes", "1"}:
        return True
    if answer in {"false", "错误", "错", "否", "no", "0"}:
        return False
    return None


def _normalize_rubric(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            criterion = _text(item.get("criterion") or item.get("point") or item.get("description"))
            if criterion:
                points = item.get("points", 1)
                try:
                    points = int(points)
                except (TypeError, ValueError):
                    points = 1
                result.append({"criterion": criterion, "points": max(points, 1)})
        else:
            criterion = _text(item)
            if criterion:
                result.append({"criterion": criterion, "points": 1})
    return result


def _normalize_hints(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): _text(item)
        for key, item in value.items()
        if _text(item)
    }


def _normalize_branches(value: Any) -> list[dict[str, str]]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            condition = _text(item.get("condition") or item.get("when"))
            action = _text(item.get("action") or item.get("next_step") or item.get("response"))
            if condition and action:
                result.append({"condition": condition, "action": action})
        else:
            text = _text(item)
            if text:
                result.append({"condition": "课堂反馈出现该情况", "action": text})
    return result


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _text(item))]


def _invalid_output(message: str, discarded: Any = None) -> AppError:
    details = {"discarded_items": discarded} if discarded is not None else None
    return AppError(
        code="classroom_activity_output_invalid",
        message=message,
        status_code=422,
        details=details,
    )


def _to_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# 课堂互动活动包",
        f"- 主题：{data['topic']}",
        f"- 预计总时长：{data['total_minutes']} 分钟 / {data['duration_minutes']} 分钟",
    ]
    if data["objectives"]:
        lines.append("- 教学目标：" + "；".join(data["objectives"]))
    for index, activity in enumerate(data["activities"], start=1):
        lines.extend(
            [
                "",
                f"## {index}. {activity['title']}",
                f"- 类型：{activity['type']}",
                f"- 用时：{activity['duration_minutes']} 分钟",
                f"- 题目：{activity['prompt']}",
            ]
        )
        if activity["options"]:
            lines.append("- 选项：" + "；".join(activity["options"]))
        if activity["answer"] not in (None, ""):
            lines.append(f"- 参考答案：{activity['answer']}")
        if activity["explanation"]:
            lines.append(f"- 解析：{activity['explanation']}")
        if activity["common_misconceptions"]:
            lines.append("- 常见误区：" + "；".join(activity["common_misconceptions"]))
        if activity["teacher_prompt"]:
            lines.append(f"- 教师提示语：{activity['teacher_prompt']}")
        if activity["differentiated_hints"]:
            lines.append("- 分层提示：" + "；".join(
                f"{key}：{value}" for key, value in activity["differentiated_hints"].items()
            ))
        if activity["rubric"]:
            lines.append("- 评分量规：" + "；".join(
                f"{item['criterion']}（{item['points']}分）" for item in activity["rubric"]
            ))
        if activity["branches"]:
            lines.append("- 分支动作：" + "；".join(
                f"{item['condition']} → {item['action']}" for item in activity["branches"]
            ))
    if data["discarded_items"]:
        lines.extend(["", "## 校验说明"])
        lines.extend(
            f"- 已跳过第 {item['index'] + 1} 项：{item['reason']}"
            for item in data["discarded_items"]
        )
    return "\n".join(lines)
