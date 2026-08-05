import json
from typing import Any, Literal

StreamEventType = Literal[
    "message_start",
    "route_decision",
    "delta",
    "tool_status",
    "artifact",
    "done",
    "error",
]

# The frontend shell relies on this fixed vocabulary; keep it in sync with the
# Stage 3 streaming contract before adding new event types.
STREAM_EVENT_TYPES: tuple[StreamEventType, ...] = (
    "message_start",
    "route_decision",
    "delta",
    "tool_status",
    "artifact",
    "done",
    "error",
)


def stream_event(event_type: StreamEventType, data: dict[str, Any]) -> str:
    """Serialize one Server-Sent Event using the shared streaming vocabulary."""

    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"
