from app.core.errors import AppError, TaskError


def test_app_error_serializes_a_stable_payload() -> None:
    error = AppError(
        code="invalid_request",
        message="The request is invalid.",
        status_code=400,
        details={"field": "name"},
    )

    assert error.to_payload() == {
        "error": {
            "code": "invalid_request",
            "message": "The request is invalid.",
            "details": {"field": "name"},
        }
    }


def test_task_error_has_a_task_safe_default_status() -> None:
    error = TaskError(code="task_failed", message="The task failed.")

    assert error.status_code == 422
