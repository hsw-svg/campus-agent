"""Create anonymous role workspaces.

Revision ID: 0002_create_anonymous_workspace
Revises: 0001_enable_pgvector
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_create_anonymous_workspace"
down_revision = "0001_enable_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anonymous_workspace",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('student', 'teacher', 'admin')", name="ck_workspace_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_anonymous_workspace_token_hash", "anonymous_workspace", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_anonymous_workspace_token_hash", table_name="anonymous_workspace")
    op.drop_table("anonymous_workspace")
