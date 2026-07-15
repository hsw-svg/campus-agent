"""Create conversation and message tables.

Revision ID: 0003_create_conversation_message
Revises: 0002_create_anonymous_workspace
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0003_create_conversation_message"
down_revision = "0002_create_anonymous_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False, server_default="新对话"),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["anonymous_workspace.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_workspace_id", "conversation", ["workspace_id"])

    op.create_table(
        "message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("tool_events", JSONB(), nullable=True),
        sa.Column("artifacts", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_message_role"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["anonymous_workspace.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_conversation_id", "message", ["conversation_id"])
    op.create_index("ix_message_workspace_id", "message", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_message_workspace_id", table_name="message")
    op.drop_index("ix_message_conversation_id", table_name="message")
    op.drop_table("message")
    op.drop_index("ix_conversation_workspace_id", table_name="conversation")
    op.drop_table("conversation")
