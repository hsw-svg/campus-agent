"""Add student course catalog, chapters, progress, and chapter context."""

from alembic import op
import sqlalchemy as sa


revision = "0013_student_course_center"
down_revision = "0012_campus_news_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("course", sa.Column("template_key", sa.String(length=64), nullable=True))
    op.add_column("course", sa.Column("teacher_name", sa.String(length=120), nullable=True))
    op.add_column("course", sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("course", sa.Column("thumbnail_key", sa.String(length=64), nullable=True))
    op.add_column("course", sa.Column("category", sa.String(length=64), nullable=True))
    op.create_unique_constraint(
        "uq_course_workspace_template_key",
        "course",
        ["workspace_id", "template_key"],
    )

    op.create_table(
        "course_chapter",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("knowledge_points", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["course.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "position", name="uq_course_chapter_position"),
    )
    op.create_index("ix_course_chapter_course_id", "course_chapter", ["course_id"])

    op.create_table(
        "student_course_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_studied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_chapter_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["anonymous_workspace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["course.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_chapter_id"], ["course_chapter.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "course_id", name="uq_student_course_progress_owner"),
    )
    op.create_index("ix_student_course_progress_workspace_id", "student_course_progress", ["workspace_id"])
    op.create_index("ix_student_course_progress_course_id", "student_course_progress", ["course_id"])

    op.create_table(
        "course_chapter_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_progress_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_progress_id"], ["student_course_progress.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["course_chapter.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_progress_id", "chapter_id", name="uq_course_chapter_progress"),
    )
    op.create_index("ix_course_chapter_progress_course_progress_id", "course_chapter_progress", ["course_progress_id"])
    op.create_index("ix_course_chapter_progress_chapter_id", "course_chapter_progress", ["chapter_id"])

    op.create_table(
        "student_course_weak_point",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_progress_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("evidence_artifact_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_progress_id"], ["student_course_progress.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["course_chapter.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_artifact_id"], ["artifact.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_course_weak_point_course_progress_id", "student_course_weak_point", ["course_progress_id"])

    op.add_column("conversation", sa.Column("chapter_id", sa.Uuid(), nullable=True))
    op.create_index("ix_conversation_chapter_id", "conversation", ["chapter_id"])
    op.create_foreign_key(
        "fk_conversation_chapter_id",
        "conversation",
        "course_chapter",
        ["chapter_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_conversation_chapter_id", "conversation", type_="foreignkey")
    op.drop_index("ix_conversation_chapter_id", table_name="conversation")
    op.drop_column("conversation", "chapter_id")
    op.drop_index("ix_student_course_weak_point_course_progress_id", table_name="student_course_weak_point")
    op.drop_table("student_course_weak_point")
    op.drop_index("ix_course_chapter_progress_chapter_id", table_name="course_chapter_progress")
    op.drop_index("ix_course_chapter_progress_course_progress_id", table_name="course_chapter_progress")
    op.drop_table("course_chapter_progress")
    op.drop_index("ix_student_course_progress_course_id", table_name="student_course_progress")
    op.drop_index("ix_student_course_progress_workspace_id", table_name="student_course_progress")
    op.drop_table("student_course_progress")
    op.drop_index("ix_course_chapter_course_id", table_name="course_chapter")
    op.drop_table("course_chapter")
    op.drop_constraint("uq_course_workspace_template_key", "course", type_="unique")
    op.drop_column("course", "category")
    op.drop_column("course", "thumbnail_key")
    op.drop_column("course", "starts_at")
    op.drop_column("course", "teacher_name")
    op.drop_column("course", "template_key")
