"""Create workspace-scoped attachments and material chunks."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


revision = "0004_attachment_chunks"
down_revision = "0003_create_conversation_message"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("scope", sa.String(length=16), server_default="conversation", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="uploaded", nullable=False),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("extracted_chars", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("scope IN ('conversation', 'workspace')", name="ck_attachment_scope"),
        sa.CheckConstraint("status IN ('uploaded', 'parsing', 'indexed', 'degraded', 'failed')", name="ck_attachment_status"),
        sa.ForeignKeyConstraint(["workspace_id"], ["anonymous_workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_attachment_workspace_id", "attachment", ["workspace_id"])
    op.create_index("ix_attachment_conversation_id", "attachment", ["conversation_id"])

    op.create_table(
        "material_chunk",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["anonymous_workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_material_chunk_attachment_id", "material_chunk", ["attachment_id"])
    op.create_index("ix_material_chunk_workspace_id", "material_chunk", ["workspace_id"])
    op.create_index("ix_material_chunk_conversation_id", "material_chunk", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_material_chunk_conversation_id", table_name="material_chunk")
    op.drop_index("ix_material_chunk_workspace_id", table_name="material_chunk")
    op.drop_index("ix_material_chunk_attachment_id", table_name="material_chunk")
    op.drop_table("material_chunk")
    op.drop_index("ix_attachment_conversation_id", table_name="attachment")
    op.drop_index("ix_attachment_workspace_id", table_name="attachment")
    op.drop_table("attachment")
