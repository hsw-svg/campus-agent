"""Stable contracts between routing, context building, and agent execution."""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


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


@dataclass(frozen=True)
class AgentRequest:
    workspace_id: UUID
    conversation_id: UUID
    role: str
    agent_id: str
    content: str
    selected_attachment_ids: tuple[UUID, ...] = ()
    selected_artifact_ids: tuple[UUID, ...] = ()
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


class AgentExecutor(Protocol):
    async def execute(self, request: AgentRequest) -> AgentResult: ...
