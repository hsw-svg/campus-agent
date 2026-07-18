from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.conversations.models import JsonColumn
from app.db.base import Base


class AgentRun(Base):
    """A workspace-scoped routing and execution record."""

    __tablename__ = "agent_run"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("anonymous_workspace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("message.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    selection_source: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    missing_inputs: Mapped[list | None] = mapped_column(JsonColumn, nullable=True)
    candidate_agent_ids: Mapped[list | None] = mapped_column(JsonColumn, nullable=True)
    selected_attachment_ids: Mapped[list | None] = mapped_column(JsonColumn, nullable=True)
    selected_artifact_ids: Mapped[list | None] = mapped_column(JsonColumn, nullable=True)
    course_id: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    parent_run_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    input_refs: Mapped[list | None] = mapped_column(JsonColumn, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="routed")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    result_message_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    artifact_status: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
