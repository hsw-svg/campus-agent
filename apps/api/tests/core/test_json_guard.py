import pytest
from pydantic import BaseModel

from app.core.errors import TaskError
from app.core.json_guard import parse_json


class Answer(BaseModel):
    value: str


def test_invalid_json_raises_a_stable_task_error() -> None:
    with pytest.raises(TaskError, match="invalid_structured_output") as exc_info:
        parse_json("not-json", Answer)

    assert exc_info.value.code == "invalid_structured_output"


def test_valid_json_is_validated_against_the_requested_model() -> None:
    assert parse_json('{"value":"ready"}', Answer) == Answer(value="ready")
