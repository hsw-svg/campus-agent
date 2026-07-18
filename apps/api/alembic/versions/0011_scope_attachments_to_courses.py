"""Scope workspace materials to an optional course."""

from alembic import op
import sqlalchemy as sa

revision = "0011_course_attachment_scope"
down_revision = "0010_courses_task_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attachment", sa.Column("course_id", sa.Uuid(), nullable=True))
    op.create_index("ix_attachment_course_id", "attachment", ["course_id"])
    op.create_foreign_key("fk_attachment_course_id", "attachment", "course", ["course_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_attachment_course_id", "attachment", type_="foreignkey")
    op.drop_index("ix_attachment_course_id", table_name="attachment")
    op.drop_column("attachment", "course_id")
