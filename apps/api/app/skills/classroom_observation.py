"""Parse classroom option counts and compute totals without an LLM."""

from dataclasses import dataclass
import re
from typing import Any

from app.core.errors import AppError


_COUNT_THEN_OPTION = re.compile(
    r"(?P<count>\d+)\s*人?\s*(?:选|选择|投|投给|choose|chose)?\s*(?P<option>[A-Za-z])\b",
    re.IGNORECASE,
)
_OPTION_THEN_COUNT = re.compile(
    r"\b(?P<option>[A-Za-z])\s*(?:选项)?\s*(?:有|为|是)?\s*[:：=]?\s*(?P<count>\d+)\s*人?",
    re.IGNORECASE,
)
_DECLARED_TOTAL = re.compile(r"(?:总人数|共(?:有)?|班级人数|应到)\s*[:：=]?\s*(?P<count>\d+)\s*人?")
_QUESTION_MARKER = re.compile(
    r"(?:第\s*[0-9一二三四五六七八九十]+\s*[题问组]|"
    r"(?:题目|问题|活动|小组)\s*[0-9一二三四五六七八九十]+)"
)


@dataclass(frozen=True)
class ClassroomObservation:
    counts: dict[str, int]
    total: int
    ratios: dict[str, float]
    note: str
    status: str = "ready"
    ambiguities: tuple[str, ...] = ()
    declared_total: int | None = None
    candidate_counts: tuple[dict[str, int], ...] = ()


class ClassroomObservationSkill:
    id = "classroom_observation_parser"
    version = "1"
    input_type = "str"
    output_type = "ClassroomObservation"
    error_codes = ("classroom_observation_incomplete", "classroom_observation_ambiguous")
    has_side_effects = False
    can_access_workspace = False

    def run(self, value: str) -> ClassroomObservation:
        matches = [*_COUNT_THEN_OPTION.finditer(value), *_OPTION_THEN_COUNT.finditer(value)]
        counts: dict[str, int] = {}
        ambiguities: list[str] = []
        candidate_counts: list[dict[str, int]] = []
        for match in matches:
            option = match.group("option").upper()
            count = int(match.group("count"))
            if option in counts and counts[option] != count:
                candidate_counts.extend((dict(counts), {option: count}))
                ambiguities.append(f"选项 {option} 出现了不同人数，无法确认对应题目。")
                continue
            counts[option] = count
        if not counts:
            raise AppError(
                code="classroom_observation_incomplete",
                message="No option counts were found in the classroom observation.",
                status_code=422,
            )
        total = sum(counts.values())
        if total <= 0:
            raise AppError(
                code="classroom_observation_incomplete",
                message="The classroom observation must contain at least one response.",
                status_code=422,
            )
        declared_match = _DECLARED_TOTAL.search(value)
        declared_total = int(declared_match.group("count")) if declared_match else None
        if declared_total is not None and declared_total != total:
            ambiguities.append(
                f"选项人数合计为 {total}，但文本声明总人数为 {declared_total}，请确认统计归属。"
            )
        markers = {
            marker.group(0)
            for marker in _QUESTION_MARKER.finditer(value)
        }
        if len(markers) > 1:
            ambiguities.append("文本包含多道题或多个活动的统计，请确认本组人数对应的活动。")
        if candidate_counts:
            # Do not expose a merged count as if it were authoritative.
            candidate_counts.insert(0, dict(counts))
        if ambiguities:
            # The first occurrence is not a safe answer when the text contains
            # multiple groups or inconsistent totals.  Keep the ambiguity and
            # require confirmation instead of presenting guessed statistics.
            counts = {}
            total = 0
        return ClassroomObservation(
            counts=counts,
            total=total,
            ratios={option: round(count / total, 4) for option, count in counts.items()}
            if total
            else {},
            note=value.strip(),
            status="needs_confirmation" if ambiguities else "ready",
            ambiguities=tuple(dict.fromkeys(ambiguities)),
            declared_total=declared_total,
            candidate_counts=tuple(candidate_counts),
        )


def observation_data(observation: ClassroomObservation) -> dict[str, Any]:
    """Serialize observation state for an API artifact without guessing."""

    data: dict[str, Any] = {
        "scope": "class",
        "status": observation.status,
        "counts": observation.counts,
        "total": observation.total,
        "ratios": observation.ratios,
        "note": observation.note,
    }
    if observation.declared_total is not None:
        data["declared_total"] = observation.declared_total
    if observation.ambiguities:
        data["ambiguities"] = list(observation.ambiguities)
    if observation.candidate_counts:
        data["candidate_counts"] = list(observation.candidate_counts)
    return data
