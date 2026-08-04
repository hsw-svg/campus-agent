"""Shared workflow guards for agent execution policy."""

from uuid import UUID


TEACHER_STANDALONE_AGENT_WORKFLOW_ID = "teacher-standalone-agent"
_EMPTY_MATERIAL_TEACHER_AGENTS = frozenset({"classroom_interaction", "course_iteration"})


def allows_empty_teacher_materials(
    *,
    role: str,
    agent_id: str,
    workflow_id: str | None,
    conversation_course_id: UUID | str | None,
) -> bool:
    """Return whether this trusted conversation may run without attachments."""

    return (
        role == "teacher"
        and agent_id in _EMPTY_MATERIAL_TEACHER_AGENTS
        and workflow_id == TEACHER_STANDALONE_AGENT_WORKFLOW_ID
        and conversation_course_id is None
    )
