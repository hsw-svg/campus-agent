from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.agents.repositories import AgentRunRepository
from app.integrations.search.bing import BingSearchProvider
from app.services.background_tasks import BackgroundTaskManager

if TYPE_CHECKING:
    from app.agents.nanobot.runner import NanobotRunner
from app.workspaces.dependencies import get_session


def get_nanobot_runner(request: Request) -> "NanobotRunner | None":
    return getattr(request.app.state, "nanobot_runner", None)


def get_bing_provider(request: Request) -> BingSearchProvider:
    return request.app.state.bing_provider


def get_background_task_manager(request: Request) -> BackgroundTaskManager:
    return request.app.state.background_task_manager


def get_agent_run_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AgentRunRepository:
    return AgentRunRepository(session)
