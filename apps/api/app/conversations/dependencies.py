from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.repositories.conversations import ConversationRepository, MessageRepository
from app.workspaces.dependencies import get_session


def get_conversation_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ConversationRepository:
    return ConversationRepository(session)


def get_message_repository(
    session: Annotated[Session, Depends(get_session)],
) -> MessageRepository:
    return MessageRepository(session)
