"""Add the current resume pointer for student workspaces."""

from alembic import op
import sqlalchemy as sa


revision = "0014_student_resume_profile"
down_revision = "0013_student_course_center"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_resume_profile",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("current_attachment_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["anonymous_workspace.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["current_attachment_id"],
            ["attachment.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("workspace_id"),
    )
    op.create_index(
        "ix_student_resume_profile_current_attachment_id",
        "student_resume_profile",
        ["current_attachment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_student_resume_profile_current_attachment_id",
        table_name="student_resume_profile",
    )
    op.drop_table("student_resume_profile")
