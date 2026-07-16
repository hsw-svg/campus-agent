from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.agents.repositories import AgentRunRepository
from app.workspaces.dependencies import get_session


def get_agent_run_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AgentRunRepository:
    return AgentRunRepository(session)
