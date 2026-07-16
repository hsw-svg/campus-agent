"""Parse classroom option counts and compute totals without an LLM."""

from dataclasses import dataclass
import re

from app.core.errors import AppError


_COUNT_THEN_OPTION = re.compile(
    r"(?P<count>\d+)\s*人?\s*(?:选|选择|投|投给|choose|chose)?\s*(?P<option>[A-Za-z])\b",
    re.IGNORECASE,
)
_OPTION_THEN_COUNT = re.compile(
    r"\b(?P<option>[A-Za-z])\s*(?:选项)?\s*[:：=]?\s*(?P<count>\d+)\s*人?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ClassroomObservation:
    counts: dict[str, int]
    total: int
    ratios: dict[str, float]
    note: str


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
        for match in matches:
            option = match.group("option").upper()
            count = int(match.group("count"))
            if option in counts and counts[option] != count:
                raise AppError(
                    code="classroom_observation_ambiguous",
                    message=f"Option {option} has more than one count.",
                    status_code=422,
                )
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
        return ClassroomObservation(
            counts=counts,
            total=total,
            ratios={option: round(count / total, 4) for option, count in counts.items()},
            note=value.strip(),
        )
