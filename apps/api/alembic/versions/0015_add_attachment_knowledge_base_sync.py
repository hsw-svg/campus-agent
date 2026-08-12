"""Track external knowledge-base synchronization for course materials."""

from alembic import op
import sqlalchemy as sa


revision = "0015_attachment_kb_sync"
down_revision = "0014_student_resume_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attachment",
        sa.Column("knowledge_base_name", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "attachment",
        sa.Column("knowledge_base_status", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "attachment",
        sa.Column("knowledge_base_task_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "attachment",
        sa.Column("knowledge_base_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attachment", "knowledge_base_message")
    op.drop_column("attachment", "knowledge_base_task_id")
    op.drop_column("attachment", "knowledge_base_status")
    op.drop_column("attachment", "knowledge_base_name")
