from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.artifacts.models import Artifact
from app.courses.models import Course  # noqa: F401
from app.db.base import Base
from app.workspaces.models import AnonymousWorkspace  # noqa: F401


def test_authoritative_artifact_fields_are_nullable_for_legacy_rows() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    columns = {item["name"]: item for item in inspect(engine).get_columns("artifact")}

    for name in (
        "object_key",
        "mime_type",
        "sha256",
        "size_bytes",
        "page_count",
        "preview_status",
        "preview_manifest",
    ):
        assert columns[name]["nullable"] is True
        assert getattr(Artifact, name) is not None


def test_presentation_migration_follows_current_head_and_uses_nullable_columns() -> None:
    migration = Path(__file__).parents[2] / "alembic" / "versions" / "0012_add_artifact_presentation.py"
    source = migration.read_text(encoding="utf-8")

    assert 'down_revision = "0011_course_attachment_scope"' in source
    assert 'revision = "0012_artifact_presentation"' in source
    assert source.count("nullable=True") == 7
