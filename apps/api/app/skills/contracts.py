from typing import Any, Protocol


class Skill(Protocol):
    id: str
    version: str
    input_type: str
    output_type: str
    error_codes: tuple[str, ...]
    has_side_effects: bool
    can_access_workspace: bool

    def run(self, value: Any) -> Any: ...


class SkillRegistry:
    def __init__(self, skills: tuple[Skill, ...] = ()) -> None:
        self._skills = {skill.id: skill for skill in skills}

    def register(self, skill: Skill) -> None:
        self._skills[skill.id] = skill

    def get(self, skill_id: str) -> Skill:
        try:
            return self._skills[skill_id]
        except KeyError as error:
            raise KeyError(f"Skill is not registered: {skill_id}") from error

    def ids(self) -> tuple[str, ...]:
        return tuple(self._skills)
