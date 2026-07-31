from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.campus_news.models import CampusNewsItem, CampusNewsSourceState
from app.integrations.campus_news import NormalizedCampusNewsItem


class CampusNewsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def states(self, source_ids: tuple[str, ...]) -> dict[str, CampusNewsSourceState]:
        if not source_ids:
            return {}
        rows = self.session.scalars(
            select(CampusNewsSourceState).where(CampusNewsSourceState.source_id.in_(source_ids))
        )
        return {row.source_id: row for row in rows}

    def list_items(self, source_ids: tuple[str, ...]) -> list[CampusNewsItem]:
        if not source_ids:
            return []
        return list(self.session.scalars(
            select(CampusNewsItem)
            .where(CampusNewsItem.source_id.in_(source_ids))
            .order_by(CampusNewsItem.published_at.desc())
        ))

    def acquire_refresh_lease(self, source_id: str, now: datetime, lease_seconds: int = 60) -> bool:
        state = self.session.scalar(
            select(CampusNewsSourceState)
            .where(CampusNewsSourceState.source_id == source_id)
            .with_for_update()
        )
        if state is None:
            state = CampusNewsSourceState(source_id=source_id)
            self.session.add(state)
            try:
                self.session.flush()
            except IntegrityError:
                self.session.rollback()
                return False
        started = _aware(state.refresh_started_at)
        if started and started > now - timedelta(seconds=lease_seconds):
            return False
        state.refresh_started_at = now
        state.last_attempt_at = now
        self._commit()
        return True

    def replace_source(self, source_id: str, items: tuple[NormalizedCampusNewsItem, ...], now: datetime) -> None:
        self.session.execute(delete(CampusNewsItem).where(CampusNewsItem.source_id == source_id))
        self.session.add_all([
            CampusNewsItem(
                source_id=item.source_id,
                category=item.category,
                title=item.title,
                summary=item.summary,
                source=item.source,
                url=item.url,
                published_at=item.published_at,
                event_end_at=item.event_end_at,
                fetched_at=now,
                fingerprint=item.fingerprint,
            )
            for item in items
        ])
        state = self.session.get(CampusNewsSourceState, source_id)
        if state is None:
            state = CampusNewsSourceState(source_id=source_id)
            self.session.add(state)
        state.last_attempt_at = now
        state.last_success_at = now
        state.refresh_started_at = None
        state.last_error = None
        self._commit()

    def mark_failure(self, source_id: str, error: str, now: datetime) -> None:
        state = self.session.get(CampusNewsSourceState, source_id)
        if state is None:
            state = CampusNewsSourceState(source_id=source_id)
            self.session.add(state)
        state.last_attempt_at = now
        state.refresh_started_at = None
        state.last_error = error[:1000]
        self._commit()

    def _commit(self) -> None:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
