from pathlib import Path


def test_migration_revision_ids_fit_alembic_version_column() -> None:
    migration_dir = Path(__file__).parents[2] / "alembic" / "versions"
    for migration in migration_dir.glob("*.py"):
        source = migration.read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.startswith("revision = "):
                revision = line.split('"', 2)[1]
                assert len(revision) <= 32, migration.name
