"""Bind DeepTutor books and spine entries to student courses."""

from alembic import op
import sqlalchemy as sa


revision = "0016_bind_course_textbooks"
down_revision = "0015_attachment_kb_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "course",
        sa.Column("deeptutor_book_id", sa.String(length=96), nullable=True),
    )
    op.create_index(
        "ix_course_deeptutor_book_id",
        "course",
        ["deeptutor_book_id"],
    )
    op.create_unique_constraint(
        "uq_course_workspace_deeptutor_book",
        "course",
        ["workspace_id", "deeptutor_book_id"],
    )
    op.add_column(
        "course_chapter",
        sa.Column("deeptutor_chapter_id", sa.String(length=96), nullable=True),
    )
    op.add_column(
        "course_chapter",
        sa.Column(
            "deeptutor_page_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.create_unique_constraint(
        "uq_course_chapter_deeptutor_chapter",
        "course_chapter",
        ["course_id", "deeptutor_chapter_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_course_chapter_deeptutor_chapter",
        "course_chapter",
        type_="unique",
    )
    op.drop_column("course_chapter", "deeptutor_page_ids")
    op.drop_column("course_chapter", "deeptutor_chapter_id")
    op.drop_constraint(
        "uq_course_workspace_deeptutor_book",
        "course",
        type_="unique",
    )
    op.drop_index("ix_course_deeptutor_book_id", table_name="course")
    op.drop_column("course", "deeptutor_book_id")
