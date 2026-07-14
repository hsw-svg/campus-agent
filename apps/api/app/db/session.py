from collections.abc import Callable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str) -> Engine:
    """Create an engine without connecting during application startup."""

    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def make_database_probe(engine: Engine) -> Callable[[], None]:
    def probe() -> None:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    return probe
