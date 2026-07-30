"""Student-specific agent runs API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.agents.dependencies import get_agent_run_repository
from app.agents.repositories import AgentHistoryRecord, AgentRunRepository
from app.core.errors import AppError
from app.workspaces.dependencies import get_current_workspace
from app.workspaces.models import AnonymousWorkspace
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.workspaces.dependencies import get_session
from app.agents.models import AgentRun
from app.conversations.models import Conversation, Message
from app.artifacts.models import Artifact

router = APIRouter(prefix="/api/student-agents", tags=["student-agents"])


class StudentArtifactResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    conversation_id: UUID
    type: str
    title: str
    content: str
    data: dict
    format: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class StudentAgentHistoryResponse(BaseModel):
    run_id: UUID
    conversation_id: UUID
    conversation_title: str
    agent_id: str | None
    status: str
    summary: str | None
    artifact: StudentArtifactResponse | None
    created_at: str
    updated_at: str


@router.get("/history", response_model=list[StudentAgentHistoryResponse])
def list_student_agent_history(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    session: Session = Depends(get_session),
) -> list[StudentAgentHistoryResponse]:
    """List agent run history for the current student workspace."""

    # Query agent runs for this student workspace
    rows = session.execute(
        select(AgentRun, Conversation, Artifact, Message)
        .join(Conversation, Conversation.id == AgentRun.conversation_id)
        .outerjoin(
            Artifact,
            (Artifact.id == AgentRun.artifact_id) & (Artifact.workspace_id == workspace.id),
        )
        .outerjoin(
            Message,
            (Message.id == AgentRun.result_message_id) & (Message.workspace_id == workspace.id),
        )
        .where(
            AgentRun.workspace_id == workspace.id,
            Conversation.workspace_id == workspace.id,
        )
        .order_by(AgentRun.created_at.desc())
        .limit(50)
    )

    records = [
        AgentHistoryRecord(
            run=run,
            conversation=conversation,
            artifact=artifact,
            result_message=result_message,
        )
        for run, conversation, artifact, result_message in rows.all()
    ]

    return [_history_response(record) for record in records]


@router.delete("/history/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_agent_history(
    run_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
) -> None:
    """Delete a student agent run."""
    run = agent_runs.get(workspace.id, run_id)
    if run is None:
        raise AppError(code="agent_run_not_found", message="Agent run was not found.", status_code=404)
    agent_runs.delete(run)


def _history_response(record: AgentHistoryRecord) -> StudentAgentHistoryResponse:
    artifact = record.artifact
    summary = record.result_message.content.strip() if record.result_message else None
    if summary and len(summary) > 240:
        summary = f"{summary[:237]}..."
    return StudentAgentHistoryResponse(
        run_id=record.run.id,
        conversation_id=record.conversation.id,
        conversation_title=record.conversation.title,
        agent_id=record.run.agent_id,
        status=record.run.status,
        summary=summary or None,
        artifact=StudentArtifactResponse.model_validate(artifact) if artifact else None,
        created_at=record.run.created_at.isoformat(),
        updated_at=record.run.updated_at.isoformat(),
    )
