"""Deterministic guards for agent output before it is persisted."""

from app.core.errors import AppError


class OutputValidationSkill:
    id = "output_validation"
    version = "1"
    input_type = "str"
    output_type = "str"
    error_codes = ("agent_output_invalid",)
    has_side_effects = False
    can_access_workspace = False

    def run(self, value: str) -> str:
        if not value.strip():
            raise AppError(
                code="agent_output_invalid",
                message="The agent produced an empty result.",
                status_code=422,
            )
        return value
