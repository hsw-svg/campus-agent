"""Deterministic class-level learning analysis.

This module deliberately does not produce student profiles.  It extracts the
small set of aggregate measures needed by a teacher, while keeping arithmetic
out of the language model path.
"""

from __future__ import annotations

import csv
import io
import math
import re
from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Any


_ANONYMOUS_HEADER_TERMS = (
    "匿名",
    "脱敏",
    "anonymous",
    "student_id",
    "student id",
    "student_no",
    "student no",
    "学员编号",
    "学生编号",
    "编号",
)
_NAME_HEADER_TERMS = ("姓名", "学生姓名", "name", "student_name")
_ATTENDANCE_TERMS = ("签到", "出勤", "到课", "attendance", "present")
_ACTIVITY_TERMS = ("课堂积极性", "积极性评分", "课堂参与", "participation", "activity")
_ASSIGNMENT_TERMS = ("作业", "homework", "assignment", "exercise", "练习", "得分", "分数", "score")
_EXCLUDED_ASSIGNMENT_TERMS = ("平均", "均分", "满分", "总分", "average", "max", "full")

_PRESENT_VALUES = {"签到", "已签到", "出勤", "到课", "正常", "present", "p", "yes", "是", "√", "1"}
_LATE_VALUES = {"迟到", "late", "l"}
_ABSENT_VALUES = {
    "缺勤",
    "缺席",
    "未签到",
    "旷课",
    "absent",
    "absence",
    "a",
    "no",
    "否",
    "0",
}
_ACTIVITY_LEVELS = {
    "非常积极": 5.0,
    "积极": 4.0,
    "一般": 3.0,
    "较低": 2.0,
    "低": 1.0,
    "high": 5.0,
    "medium": 3.0,
    "low": 1.0,
}


@dataclass(frozen=True)
class LearningAnalysisResult:
    """A class-level result suitable for an artifact and a chat response."""

    data: dict[str, Any]
    markdown: str


def analyze_learning_table(text: str, *, filename: str = "") -> LearningAnalysisResult:
    """Analyze a parsed CSV/XLSX table without retaining student-level data."""

    rows, headers = _extract_table(text)
    anonymous_index = _find_header(headers, _ANONYMOUS_HEADER_TERMS)
    name_index = _find_header(headers, _NAME_HEADER_TERMS)
    attendance_indices = _find_attendance_indices(headers)
    activity_indices = _find_activity_indices(headers)
    assignment_indices = _find_assignment_indices(headers)
    full_mark_index = _find_header(headers, ("满分", "full_mark", "max_score", "total"))

    errors: list[str] = []
    warnings: list[str] = []
    if anonymous_index is None:
        errors.append("anonymous_id_required")
    if name_index is not None and anonymous_index is None:
        warnings.append("name_field_is_not_used")
    if not attendance_indices:
        warnings.append("attendance_fields_not_found")
    if not activity_indices:
        warnings.append("activity_fields_not_found")
    if not assignment_indices:
        warnings.append("assignment_fields_not_found")
    if not headers:
        errors.append("table_header_not_found")

    valid_rows = [row for row in rows if anonymous_index is not None and _cell(row, anonymous_index)]
    if not valid_rows and anonymous_index is not None:
        errors.append("anonymous_rows_not_found")
    if not (attendance_indices or activity_indices or assignment_indices):
        errors.append("learning_metrics_not_found")

    course_profile = _build_course_profile(headers, valid_rows, filename)
    attendance = _aggregate_attendance(valid_rows, attendance_indices)
    activity = _aggregate_activity(valid_rows, activity_indices)
    assignments = _aggregate_assignments(valid_rows, headers, assignment_indices, full_mark_index)
    trend = _build_trend(assignments)
    weak_points = sorted(
        [
            {
                "name": item["name"],
                "average_percent": item["average_percent"],
            }
            for item in assignments
        ],
        key=lambda item: (item["average_percent"], item["name"]),
    )[:3]
    guidance = _build_guidance(attendance, activity, assignments, trend)

    data: dict[str, Any] = {
        "scope": "class",
        "student_count": len(valid_rows),
        "course_profile": course_profile,
        "field_mapping": {
            "anonymous_id": headers[anonymous_index] if anonymous_index is not None else None,
            "attendance": [headers[index] for index in attendance_indices],
            "activity": [headers[index] for index in activity_indices],
            "assignments": [headers[index] for index in assignment_indices],
        },
        "attendance": attendance,
        "activity": activity,
        "assignments": assignments,
        "trend": trend,
        "weak_points": weak_points,
        "guidance": guidance,
        "validation": {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "row_count": len(rows),
        },
    }
    return LearningAnalysisResult(data=data, markdown=_to_markdown(data))


def _extract_table(text: str) -> tuple[list[list[str]], list[str]]:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n") if line.strip()]
    lines = [line for line in lines if not line.startswith("[")]
    parsed = [_split_line(line) for line in lines]
    header_position = next(
        (index for index, fields in enumerate(parsed) if _looks_like_header(fields)),
        None,
    )
    if header_position is None:
        return [], []
    headers = [field.strip() for field in parsed[header_position]]
    rows: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for fields in parsed[header_position + 1 :]:
        normalized = fields[: len(headers)] + [""] * max(0, len(headers) - len(fields))
        normalized = normalized[: len(headers)]
        if not any(normalized):
            continue
        # Attachment chunks overlap. Deduplicate by the anonymous identifier
        # when possible, otherwise retain the row for validation diagnostics.
        anonymous_index = _find_header(headers, _ANONYMOUS_HEADER_TERMS)
        key = tuple(normalized) if anonymous_index is None else (normalized[anonymous_index],)
        if anonymous_index is not None and key[0] and key in seen:
            continue
        if anonymous_index is not None and key[0]:
            seen.add(key)
        rows.append(normalized)
    return rows, headers


def _split_line(line: str) -> list[str]:
    if "|" in line:
        return [field.strip() for field in line.split("|")]
    return [field.strip() for field in next(csv.reader(io.StringIO(line)), [])]


def _looks_like_header(fields: list[str]) -> bool:
    if len(fields) < 2:
        return False
    normalized = " ".join(fields).lower()
    return any(term in normalized for term in _ANONYMOUS_HEADER_TERMS) and any(
        term in normalized for term in (*_ATTENDANCE_TERMS, *_ACTIVITY_TERMS, *_ASSIGNMENT_TERMS)
    )


def _find_header(headers: list[str], terms: tuple[str, ...]) -> int | None:
    for index, header in enumerate(headers):
        normalized = header.strip().lower()
        if any(term.lower() in normalized for term in terms):
            return index
    return None


def _find_attendance_indices(headers: list[str]) -> list[int]:
    return [
        index
        for index, header in enumerate(headers)
        if any(term in header.lower() for term in _ATTENDANCE_TERMS)
        and not any(term in header.lower() for term in ("率", "次数", "rate", "count"))
    ]


def _find_activity_indices(headers: list[str]) -> list[int]:
    return [index for index, header in enumerate(headers) if any(term in header.lower() for term in _ACTIVITY_TERMS)]


def _find_assignment_indices(headers: list[str]) -> list[int]:
    return [
        index
        for index, header in enumerate(headers)
        if any(term in header.lower() for term in _ASSIGNMENT_TERMS)
        and not any(term in header.lower() for term in _EXCLUDED_ASSIGNMENT_TERMS)
    ]


def _aggregate_attendance(rows: list[list[str]], indices: list[int]) -> dict[str, Any]:
    counts = Counter(present=0, late=0, absent=0, unknown=0)
    for row in rows:
        for index in indices:
            value = _normalize(_cell(row, index))
            if value in _PRESENT_VALUES:
                counts["present"] += 1
            elif value in _LATE_VALUES:
                counts["late"] += 1
            elif value in _ABSENT_VALUES:
                counts["absent"] += 1
            elif value:
                number = _number(value)
                if number == 1:
                    counts["present"] += 1
                elif number == 0:
                    counts["absent"] += 1
                else:
                    counts["unknown"] += 1
            else:
                counts["unknown"] += 1
    total = len(rows) * len(indices)
    attended = counts["present"] + counts["late"]
    return {
        "sessions": len(indices),
        "present": counts["present"],
        "late": counts["late"],
        "absent": counts["absent"],
        "unknown": counts["unknown"],
        "rate": _ratio(attended, total),
        "late_rate": _ratio(counts["late"], total),
        "absence_rate": _ratio(counts["absent"], total),
    }


def _aggregate_activity(rows: list[list[str]], indices: list[int]) -> dict[str, Any]:
    values: list[float] = []
    distribution: Counter[str] = Counter()
    for row in rows:
        for index in indices:
            raw = _normalize(_cell(row, index))
            number = _number(raw)
            if number is None:
                number = _ACTIVITY_LEVELS.get(raw)
            if number is not None and math.isfinite(number):
                values.append(number)
            if raw:
                distribution[raw] += 1
    return {
        "average": _average(values),
        "scale": "5-point" if values and max(values) <= 5 else None,
        "distribution": dict(sorted(distribution.items())),
        "sample_count": len(values),
    }


def _aggregate_assignments(
    rows: list[list[str]],
    headers: list[str],
    indices: list[int],
    full_mark_index: int | None,
) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    for index in indices:
        values: list[float] = []
        percentages: list[float] = []
        for row in rows:
            score = _number(_cell(row, index))
            if score is None:
                continue
            values.append(score)
            full_mark = _number(_cell(row, full_mark_index)) if full_mark_index is not None else None
            full_mark = full_mark if full_mark and full_mark > 0 else 100.0
            percentages.append(score / full_mark * 100)
        assignments.append(
            {
                "name": headers[index],
                "average": _average(values),
                "average_percent": _average(percentages),
                "score_count": len(values),
                "completion_rate": _ratio(len(values), len(rows)),
            }
        )
    return assignments


def _build_trend(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    values = [item["average_percent"] for item in assignments if item["average_percent"] is not None]
    if len(values) < 2:
        return {"direction": "insufficient_data", "delta": None}
    delta = values[-1] - values[0]
    direction = "improving" if delta > 2 else "declining" if delta < -2 else "stable"
    return {"direction": direction, "delta": delta}


def _build_course_profile(headers: list[str], rows: list[list[str]], filename: str) -> dict[str, Any]:
    course_index = _find_header(headers, ("课程", "course"))
    period_index = _find_header(headers, ("数据周期", "周期", "period", "date range"))
    chapter_index = _find_header(headers, ("章节", "章节范围", "chapter", "topic"))
    courses = _unique_values(rows, course_index)
    periods = _unique_values(rows, period_index)
    chapters = _unique_values(rows, chapter_index)
    course = courses[0] if courses else _course_from_filename(filename)
    return {
        "course": course,
        "period": periods[0] if periods else None,
        "chapters": chapters[:10],
        "assessment_count": len(_find_assignment_indices(headers)),
    }


def _build_guidance(
    attendance: dict[str, Any],
    activity: dict[str, Any],
    assignments: list[dict[str, Any]],
    trend: dict[str, Any],
) -> list[str]:
    guidance: list[str] = []
    rate = attendance["rate"]
    if rate is not None and rate < 0.85:
        guidance.append("出勤稳定性偏低，建议在新知识引入前增加签到提醒和低门槛复习，避免缺课学生直接掉队。")
    activity_average = activity["average"]
    if activity_average is not None and activity_average < 3.5:
        guidance.append("课堂积极性仍有提升空间，建议缩短连续讲授段，增加即时提问、代码演示和同伴讨论。")
    if trend["direction"] == "declining":
        guidance.append("多次作业成绩呈下降趋势，建议放慢后续内容推进，将大任务拆成阶段性练习并及时反馈。")
    if assignments:
        weakest = min(assignments, key=lambda item: item["average_percent"] or float("inf"))
        if weakest["average_percent"] is not None and weakest["average_percent"] < 70:
            guidance.append(f"建议回到“{weakest['name']}”对应知识点，先用示例拆解，再安排由易到难的迁移练习。")
    if not guidance:
        guidance.append("班级整体状态较稳定，可保持当前节奏，并通过综合任务检验知识迁移和综合应用。")
    return guidance


def _to_markdown(data: dict[str, Any]) -> str:
    attendance = data["attendance"]
    activity = data["activity"]
    profile = data["course_profile"]
    lines = [
        "# 班级整体学情分析",
        "",
        "> 本报告只分析班级整体学习情况，用于指导教学方式与节奏，不生成学生个体画像。",
        "",
        "## 数据校验",
        "",
        f"- 数据范围：{profile.get('course') or '未识别课程'}；样本数：{data['student_count']} 人",
        f"- 字段校验：{'通过' if data['validation']['valid'] else '未通过'}",
        "",
        "## 课程画像",
        "",
        f"- 课程：{profile.get('course') or '未提供'}",
        f"- 数据周期：{profile.get('period') or '未提供'}",
        f"- 章节范围：{'、'.join(profile.get('chapters') or ['未提供'])}",
        f"- 作业次数：{profile.get('assessment_count', 0)}",
        "",
        "## 班级整体统计",
        "",
        f"- 出勤率：{_format_percent(attendance.get('rate'))}；迟到率：{_format_percent(attendance.get('late_rate'))}；缺勤率：{_format_percent(attendance.get('absence_rate'))}",
        f"- 课堂积极性平均分：{_format_number(activity.get('average'))}（{activity.get('sample_count', 0)} 个观测值）",
        "",
        "### 多次作业表现",
        "",
        "| 作业 | 班级平均分 | 得分率 | 完成率 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in data["assignments"]:
        lines.append(
            f"| {item['name']} | {_format_number(item['average'])} | {_format_percent(item['average_percent'] / 100 if item['average_percent'] is not None else None)} | {_format_percent(item['completion_rate'])} |"
        )
    lines.extend(["", "## 薄弱点", ""])
    if data["weak_points"]:
        lines.extend(f"- {item['name']}：平均得分率 {_format_percent(item['average_percent'] / 100)}" for item in data["weak_points"])
    else:
        lines.append("- 当前数据未识别出可比较的作业薄弱点。")
    lines.extend(["", "## 对教学方式与节奏的建议", ""])
    lines.extend(f"- {item}" for item in data["guidance"])
    return "\n".join(lines)


def _cell(row: list[str], index: int | None) -> str:
    return row[index].strip() if index is not None and index < len(row) else ""


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def _number(value: str) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "").replace("%", "")
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _average(values: list[float]) -> float | None:
    return mean(values) if values else None


def _unique_values(rows: list[list[str]], index: int | None) -> list[str]:
    values: list[str] = []
    for row in rows:
        value = _cell(row, index)
        if value and value not in values:
            values.append(value)
    return values


def _course_from_filename(filename: str) -> str | None:
    stem = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0]
    if not stem or stem.lower() in {"scores", "score", "data", "学生成绩"}:
        return None
    return stem.replace("_", " ")


def _format_number(value: float | None) -> str:
    return "未提供" if value is None else f"{value:.2f}".rstrip("0").rstrip(".")


def _format_percent(value: float | None) -> str:
    return "未提供" if value is None else f"{value * 100:.1f}%"
