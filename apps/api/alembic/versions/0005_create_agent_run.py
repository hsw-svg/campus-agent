"""Create workspace-scoped agent run records.

Revision ID: 0005_create_agent_run
Revises: 0004_attachment_chunks
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0005_create_agent_run"
down_revision = "0004_attachment_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("selection_source", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("missing_inputs", JSONB(), nullable=True),
        sa.Column("candidate_agent_ids", JSONB(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="routed"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column("result_message_id", sa.Uuid(), nullable=True),
        sa.Column("artifact_status", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["anonymous_workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["message.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_run_workspace_id", "agent_run", ["workspace_id"])
    op.create_index("ix_agent_run_conversation_id", "agent_run", ["conversation_id"])
    op.create_index("ix_agent_run_message_id", "agent_run", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_run_message_id", table_name="agent_run")
    op.drop_index("ix_agent_run_conversation_id", table_name="agent_run")
    op.drop_index("ix_agent_run_workspace_id", table_name="agent_run")
    op.drop_table("agent_run")
