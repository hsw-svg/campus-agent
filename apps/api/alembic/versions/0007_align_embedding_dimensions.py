"""Align material chunk embeddings with the configured model dimensions.

Revision ID: 0007_align_embedding_dimensions
Revises: 0006_create_artifact
Create Date: 2026-07-16
"""

from alembic import op
from pgvector.sqlalchemy import Vector


revision = "0007_align_embedding_dimensions"
down_revision = "0006_create_artifact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "material_chunk",
        "embedding",
        existing_type=Vector(1536),
        type_=Vector(1024),
        postgresql_using="embedding::vector(1024)",
    )


def downgrade() -> None:
    op.alter_column(
        "material_chunk",
        "embedding",
        existing_type=Vector(1024),
        type_=Vector(1536),
        postgresql_using="embedding::vector(1536)",
    )
