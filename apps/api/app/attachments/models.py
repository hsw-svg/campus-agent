from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.conversations.models import JsonColumn
from app.core.config import get_settings
from app.db.base import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - the production dependency provides this
    Vector = None


EmbeddingColumn = (
    JSON().with_variant(Vector(get_settings().embedding_dimensions), "postgresql")
    if Vector is not None
    else JsonColumn
)


class Attachment(Base):
    __tablename__ = "attachment"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("anonymous_workspace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    course_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course.id", ondelete="SET NULL"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="conversation")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="uploaded")
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_chars: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["MaterialChunk"]] = relationship(
        back_populates="attachment", cascade="all, delete-orphan", passive_deletes=True
    )


class MaterialChunk(Base):
    __tablename__ = "material_chunk"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    attachment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attachment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("anonymous_workspace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JsonColumn, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingColumn, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    attachment: Mapped[Attachment] = relationship(back_populates="chunks")
