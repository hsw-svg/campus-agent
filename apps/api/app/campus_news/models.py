from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class CampusNewsSourceState(Base):
    __tablename__ = "campus_news_source_state"

    source_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))


class CampusNewsItem(Base):
    __tablename__ = "campus_news_item"
    __table_args__ = (UniqueConstraint("source_id", "fingerprint", name="uq_campus_news_source_fingerprint"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
