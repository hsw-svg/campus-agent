"""Add nullable authoritative presentation metadata to artifacts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012_artifact_presentation"
down_revision = "0011_course_attachment_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artifact", sa.Column("object_key", sa.String(length=1024), nullable=True))
    op.add_column("artifact", sa.Column("mime_type", sa.String(length=255), nullable=True))
    op.add_column("artifact", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column("artifact", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("artifact", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column("artifact", sa.Column("preview_status", sa.String(length=32), nullable=True))
    op.add_column("artifact", sa.Column("preview_manifest", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("artifact", "preview_manifest")
    op.drop_column("artifact", "preview_status")
    op.drop_column("artifact", "page_count")
    op.drop_column("artifact", "size_bytes")
    op.drop_column("artifact", "sha256")
    op.drop_column("artifact", "mime_type")
    op.drop_column("artifact", "object_key")
