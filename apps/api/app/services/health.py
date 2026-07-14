from collections.abc import Callable
from typing import Any, Protocol


class ConfigurableProvider(Protocol):
    @property
    def is_configured(self) -> bool: ...


def build_health_report(
    database_probe: Callable[[], None],
    chat_provider: ConfigurableProvider,
    embedding_provider: ConfigurableProvider,
) -> dict[str, Any]:
    """Report optional dependency state without failing the health endpoint."""

    try:
        database_probe()
        database_component: dict[str, str] = {"status": "healthy"}
    except Exception:
        database_component = {
            "status": "unhealthy",
            "detail": "Database connection failed.",
        }

    chat_component = {
        "status": "configured" if chat_provider.is_configured else "unconfigured"
    }
    embedding_component = {
        "status": "configured" if embedding_provider.is_configured else "unconfigured"
    }
    components = {
        "database": database_component,
        "chat_model": chat_component,
        "embedding_model": embedding_component,
    }
    is_healthy = (
        database_component["status"] == "healthy"
        and chat_provider.is_configured
        and embedding_provider.is_configured
    )
    return {"status": "healthy" if is_healthy else "degraded", "components": components}
