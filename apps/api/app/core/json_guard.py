from typing import TypeVar

from pydantic import TypeAdapter, ValidationError

from app.core.errors import TaskError


T = TypeVar("T")


def parse_json(raw: str, model: type[T]) -> T:
    """Parse structured model output without attempting to repair invalid JSON."""

    try:
        return TypeAdapter(model).validate_json(raw)
    except (ValidationError, ValueError) as error:
        raise TaskError(
            code="invalid_structured_output",
            message="The model returned invalid structured output.",
            details={"reason": str(error)},
        ) from error
