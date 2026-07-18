"""Create course containers and attach tasks to an optional course."""

from alembic import op
import sqlalchemy as sa

revision = "0010_courses_task_links"
down_revision = "0009_agent_run_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "course",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["anonymous_workspace.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_workspace_id", "course", ["workspace_id"])
    op.add_column("conversation", sa.Column("course_id", sa.Uuid(), nullable=True))
    op.create_index("ix_conversation_course_id", "conversation", ["course_id"])
    op.create_foreign_key("fk_conversation_course_id", "conversation", "course", ["course_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_conversation_course_id", "conversation", type_="foreignkey")
    op.drop_index("ix_conversation_course_id", table_name="conversation")
    op.drop_column("conversation", "course_id")
    op.drop_index("ix_course_workspace_id", table_name="course")
    op.drop_table("course")
