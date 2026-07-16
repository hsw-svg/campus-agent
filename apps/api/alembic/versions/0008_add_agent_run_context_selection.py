"""Persist explicit context selections for retryable agent runs."""

from alembic import op
import sqlalchemy as sa


revision = "0008_agent_run_context_selection"
down_revision = "0007_align_embedding_dimensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_run", sa.Column("selected_attachment_ids", sa.JSON(), nullable=True))
    op.add_column("agent_run", sa.Column("selected_artifact_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_run", "selected_artifact_ids")
    op.drop_column("agent_run", "selected_attachment_ids")
