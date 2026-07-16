"""Create workspace-scoped generated artifacts.

Revision ID: 0006_create_artifact
Revises: 0005_create_agent_run
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0006_create_artifact"
down_revision = "0005_create_agent_run"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column("format", sa.String(length=24), nullable=False, server_default="markdown"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["anonymous_workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifact_workspace_id", "artifact", ["workspace_id"])
    op.create_index("ix_artifact_conversation_id", "artifact", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_artifact_conversation_id", table_name="artifact")
    op.drop_index("ix_artifact_workspace_id", table_name="artifact")
    op.drop_table("artifact")
