from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.campus_news.repositories import CampusNewsRepository
from app.integrations.campus_news import CampusNewsSourceError, parse_sources
from app.services.campus_news import (
    invalid_config_response,
    live_response,
    refresh_in_background,
    sample_response,
)
from app.workspaces.dependencies import get_session
from app.core.errors import AppError


router = APIRouter(prefix="/api/campus-news", tags=["campus-news"])


class CampusNewsItemResponse(BaseModel):
    id: str
    category: Literal["news", "activity", "notice"]
    title: str
    published_at: datetime
    event_end_at: datetime | None
    source: str
    summary: str | None
    url: str | None


class CampusNewsResponse(BaseModel):
    mode: Literal["sample", "live"]
    status: Literal["fresh", "stale", "degraded"]
    refreshing: bool
    last_success_at: datetime | None
    items: list[CampusNewsItemResponse]


@router.get("", response_model=CampusNewsResponse)
async def list_campus_news(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict:
    settings = request.app.state.settings
    if not settings.campus_news_sources_json.strip():
        return sample_response()
    try:
        sources = parse_sources(settings.campus_news_sources_json)
    except CampusNewsSourceError:
        return invalid_config_response()
    try:
        response, should_refresh = await live_response(
            CampusNewsRepository(session),
            sources,
            refresh_seconds=settings.campus_news_refresh_seconds,
            max_stale_seconds=settings.campus_news_max_stale_seconds,
            timeout_seconds=settings.campus_news_request_timeout_seconds,
        )
    except SQLAlchemyError as error:
        raise AppError(
            code="campus_news_cache_unavailable",
            message="Campus news cache is temporarily unavailable.",
            status_code=503,
        ) from error
    if should_refresh:
        background_tasks.add_task(
            refresh_in_background,
            request.app.state.session_factory,
            sources,
            settings.campus_news_request_timeout_seconds,
        )
    return response
