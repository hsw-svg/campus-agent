"""Add lightweight course and teaching workflow references to agent runs."""

from alembic import op
import sqlalchemy as sa


revision = "0009_agent_run_workflow"
down_revision = "0008_agent_run_context_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_run", sa.Column("course_id", sa.String(length=96), nullable=True))
    op.add_column("agent_run", sa.Column("workflow_id", sa.String(length=96), nullable=True))
    op.add_column("agent_run", sa.Column("parent_run_id", sa.Uuid(), nullable=True))
    op.add_column("agent_run", sa.Column("input_refs", sa.JSON(), nullable=True))
    op.create_index("ix_agent_run_course_id", "agent_run", ["course_id"])
    op.create_index("ix_agent_run_workflow_id", "agent_run", ["workflow_id"])
    op.create_index("ix_agent_run_parent_run_id", "agent_run", ["parent_run_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_run_parent_run_id", table_name="agent_run")
    op.drop_index("ix_agent_run_workflow_id", table_name="agent_run")
    op.drop_index("ix_agent_run_course_id", table_name="agent_run")
    op.drop_column("agent_run", "input_refs")
    op.drop_column("agent_run", "parent_run_id")
    op.drop_column("agent_run", "workflow_id")
    op.drop_column("agent_run", "course_id")
