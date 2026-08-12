"""Stable contracts between routing, context building, and agent execution."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from uuid import UUID

from app.courses.context import CourseLearningContext


AgentExecutorId = str


@dataclass(frozen=True)
class InputContract:
    required_fields: tuple[str, ...] = ("content",)
    requires_attachments: bool = False
    accepted_attachment_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextPolicy:
    id: str
    requires_explicit_attachments: bool = False
    allow_implicit_conversation_attachments: bool = True
    allow_workspace_attachments: bool = False
    exclude_learning_details: bool = False
    include_history: bool = True
    allow_raw_row_sources: bool = True


@dataclass(frozen=True)
class ContextSource:
    attachment_id: UUID
    filename: str
    excerpt: str
    page_number: int | None = None


@dataclass(frozen=True)
class ContextArtifact:
    """A selected generated result made available to an executor."""

    id: UUID
    type: str
    title: str
    content: str
    data: dict[str, Any]
    format: str = "markdown"


@dataclass(frozen=True)
class AgentContext:
    messages: tuple[dict[str, str], ...] = ()
    sources: tuple[ContextSource, ...] = ()
    attachment_text: str = ""
    attachment_filenames: tuple[str, ...] = ()
    selected_artifacts: tuple[ContextArtifact, ...] = ()
    course: CourseLearningContext | None = None


@dataclass(frozen=True)
class AgentRequest:
    workspace_id: UUID
    conversation_id: UUID
    role: str
    agent_id: str
    content: str
    selected_attachment_ids: tuple[UUID, ...] = ()
    selected_artifact_ids: tuple[UUID, ...] = ()
    course_id: str | None = None
    workflow_id: str | None = None
    allow_empty_materials: bool = False
    parent_run_id: UUID | None = None
    input_refs: tuple[str, ...] = ()
    context: AgentContext = field(default_factory=AgentContext)


@dataclass(frozen=True)
class AgentArtifact:
    type: str
    title: str
    content: str
    data: dict[str, Any]
    format: str = "markdown"


@dataclass(frozen=True)
class AgentResult:
    text: str
    structured_data: dict[str, Any] | None = None
    citations: tuple[ContextSource, ...] = ()
    artifact: AgentArtifact | None = None
    artifacts: tuple[AgentArtifact, ...] = ()
    validation: dict[str, Any] | None = None
    warnings: tuple[str, ...] = ()


AgentProgressPhase = Literal[
    "routing",
    "context",
    "retrieval",
    "model",
    "validation",
    "artifact",
    "complete",
]
AgentProgressState = Literal["active", "completed", "failed"]


@dataclass(frozen=True)
class AgentProgress:
    step_id: str
    phase: AgentProgressPhase
    state: AgentProgressState
    label: str
    detail: str | None = None
    count: int | None = None


@dataclass(frozen=True)
class AgentExecutionEvent:
    """Internal event emitted by an executor before it crosses the SSE boundary."""

    type: Literal["status", "delta", "result"]
    progress: AgentProgress | None = None
    text: str | None = None
    result: AgentResult | None = None


def progress_event(
    *,
    step_id: str,
    phase: AgentProgressPhase,
    state: AgentProgressState,
    label: str,
    detail: str | None = None,
    count: int | None = None,
) -> AgentExecutionEvent:
    return AgentExecutionEvent(
        type="status",
        progress=AgentProgress(
            step_id=step_id,
            phase=phase,
            state=state,
            label=label,
            detail=detail,
            count=count,
        ),
    )


def delta_event(text: str) -> AgentExecutionEvent:
    return AgentExecutionEvent(type="delta", text=text)


def result_event(result: AgentResult) -> AgentExecutionEvent:
    return AgentExecutionEvent(type="result", result=result)


class AgentExecutor(Protocol):
    async def execute(self, request: AgentRequest) -> AgentResult: ...


class StreamingAgentExecutor(Protocol):
    def stream(self, request: AgentRequest) -> AsyncIterator[AgentExecutionEvent]: ...
