from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.conversations.models import Conversation, Message


class ConversationRepository:
    """Conversation access that always constrains queries to one workspace."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        workspace_id: UUID,
        title: str,
        agent_id: str | None,
        course_id: UUID | None = None,
        chapter_id: UUID | None = None,
    ) -> Conversation:
        conversation = Conversation(
            workspace_id=workspace_id,
            title=title,
            agent_id=agent_id,
            course_id=course_id,
            chapter_id=chapter_id,
        )
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def list_for_workspace(self, workspace_id: UUID) -> list[Conversation]:
        return list(
            self.session.scalars(
                select(Conversation)
                .where(Conversation.workspace_id == workspace_id)
                .order_by(Conversation.updated_at.desc())
            )
        )

    def get(self, workspace_id: UUID, conversation_id: UUID) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
            )
        )

    def set_agent(self, conversation: Conversation, agent_id: str | None) -> Conversation:
        conversation.agent_id = agent_id
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def rename(self, conversation: Conversation, title: str) -> Conversation:
        conversation.title = title
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def touch(self, conversation: Conversation) -> None:
        # Bump ``updated_at`` so the sidebar keeps active conversations on top.
        conversation.updated_at = datetime.now(timezone.utc)
        self.session.commit()

    def delete(self, conversation: Conversation) -> None:
        self.session.delete(conversation)
        self.session.commit()


class MessageRepository:
    """Message access scoped to a workspace and its conversation."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        role: str,
        content: str,
        agent_id: str | None = None,
        tool_events: list | None = None,
        artifacts: list | None = None,
    ) -> Message:
        message = Message(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            agent_id=agent_id,
            tool_events=tool_events,
            artifacts=artifacts,
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def list_for_conversation(
        self, workspace_id: UUID, conversation_id: UUID
    ) -> list[Message]:
        return list(
            self.session.scalars(
                select(Message)
                .where(
                    Message.workspace_id == workspace_id,
                    Message.conversation_id == conversation_id,
                )
                .order_by(Message.created_at)
            )
        )

    def get(self, workspace_id: UUID, message_id: UUID) -> Message | None:
        return self.session.scalar(
            select(Message).where(
                Message.id == message_id,
                Message.workspace_id == workspace_id,
            )
        )
