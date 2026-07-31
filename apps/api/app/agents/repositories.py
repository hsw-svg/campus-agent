from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.models import AgentRun
from app.artifacts.models import Artifact
from app.conversations.models import Conversation, Message


@dataclass(frozen=True)
class AgentHistoryRecord:
    """One course-scoped run with its optional result and display context."""

    run: AgentRun
    conversation: Conversation
    artifact: Artifact | None
    result_message: Message | None


class AgentRunRepository:
    """Agent run access that always includes the caller's workspace."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values) -> AgentRun:
        run = AgentRun(**values)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get(self, workspace_id: UUID, run_id: UUID) -> AgentRun | None:
        return self.session.scalar(
            select(AgentRun).where(
                AgentRun.id == run_id,
                AgentRun.workspace_id == workspace_id,
            )
        )

    def list_for_course(self, workspace_id: UUID, course_id: UUID) -> list[AgentHistoryRecord]:
        rows = self.session.execute(
            select(AgentRun, Conversation, Artifact, Message)
            .join(Conversation, Conversation.id == AgentRun.conversation_id)
            .outerjoin(
                Artifact,
                (Artifact.id == AgentRun.artifact_id) & (Artifact.workspace_id == workspace_id),
            )
            .outerjoin(
                Message,
                (Message.id == AgentRun.result_message_id) & (Message.workspace_id == workspace_id),
            )
            .where(
                AgentRun.workspace_id == workspace_id,
                Conversation.workspace_id == workspace_id,
                Conversation.course_id == course_id,
            )
            .order_by(AgentRun.created_at.desc())
        )
        return [
            AgentHistoryRecord(
                run=run,
                conversation=conversation,
                artifact=artifact,
                result_message=result_message,
            )
            for run, conversation, artifact, result_message in rows.all()
        ]

    def list_for_agent(
        self, workspace_id: UUID, agent_id: str
    ) -> list[AgentHistoryRecord]:
        rows = self.session.execute(
            select(AgentRun, Conversation, Artifact, Message)
            .join(Conversation, Conversation.id == AgentRun.conversation_id)
            .outerjoin(
                Artifact,
                (Artifact.id == AgentRun.artifact_id)
                & (Artifact.workspace_id == workspace_id),
            )
            .outerjoin(
                Message,
                (Message.id == AgentRun.result_message_id)
                & (Message.workspace_id == workspace_id),
            )
            .where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.agent_id == agent_id,
                Conversation.workspace_id == workspace_id,
            )
            .order_by(AgentRun.created_at.desc())
        )
        return [
            AgentHistoryRecord(
                run=run,
                conversation=conversation,
                artifact=artifact,
                result_message=result_message,
            )
            for run, conversation, artifact, result_message in rows.all()
        ]

    def update(self, run: AgentRun, **values) -> AgentRun:
        for key, value in values.items():
            setattr(run, key, value)
        self.session.commit()
        self.session.refresh(run)
        return run

    def delete(self, run: AgentRun) -> None:
        self.session.delete(run)
        self.session.commit()
