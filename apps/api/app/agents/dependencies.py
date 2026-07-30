from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.agents.repositories import AgentRunRepository
from app.agents.router import AgentRouter
from app.workspaces.dependencies import get_session


def get_agent_run_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AgentRunRepository:
    return AgentRunRepository(session)


def get_agent_router(request: Request) -> AgentRouter:
    return AgentRouter(
        classifier=request.app.state.chat_provider,
        candidate_retriever=request.app.state.intent_candidate_retriever,
    )
