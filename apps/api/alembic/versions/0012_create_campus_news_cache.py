"""Create campus news source state and item cache."""

from alembic import op
import sqlalchemy as sa


revision = "0012_campus_news_cache"
down_revision = "0011_course_attachment_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campus_news_source_state",
        sa.Column("source_id", sa.String(length=96), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_table(
        "campus_news_item",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=96), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "fingerprint", name="uq_campus_news_source_fingerprint"),
    )
    op.create_index("ix_campus_news_item_source_id", "campus_news_item", ["source_id"])
    op.create_index("ix_campus_news_item_category", "campus_news_item", ["category"])
    op.create_index("ix_campus_news_item_published_at", "campus_news_item", ["published_at"])


def downgrade() -> None:
    op.drop_index("ix_campus_news_item_published_at", table_name="campus_news_item")
    op.drop_index("ix_campus_news_item_category", table_name="campus_news_item")
    op.drop_index("ix_campus_news_item_source_id", table_name="campus_news_item")
    op.drop_table("campus_news_item")
    op.drop_table("campus_news_source_state")
