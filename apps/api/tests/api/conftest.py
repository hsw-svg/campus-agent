from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app

# Import models so their tables register on the shared metadata before create_all.
from app.conversations import models as _conversation_models  # noqa: F401
from app.workspaces import models as _workspace_models  # noqa: F401


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite ignores foreign keys unless asked; enable them so ON DELETE CASCADE
    # behaves like PostgreSQL and workspace deletion truly removes owned rows.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    app = create_app(Settings(database_url="sqlite://"))
    app.state.session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with TestClient(app) as test_client:
        yield test_client


def make_workspace(client: TestClient, role: str = "student") -> str:
    """Create a workspace and return its one-time token."""

    response = client.post("/api/workspaces", json={"role": role})
    assert response.status_code == 201
    return response.json()["token"]
