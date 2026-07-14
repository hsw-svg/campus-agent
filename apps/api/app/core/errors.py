from typing import Any


class AppError(Exception):
    """An expected application failure with a stable API representation."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(f"{code}: {message}")

    def to_payload(self) -> dict[str, dict[str, Any]]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class TaskError(AppError):
    """An application error raised while handling a task or model response."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=422, details=details)
