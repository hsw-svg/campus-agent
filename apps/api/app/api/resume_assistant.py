from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.agents.dependencies import get_agent_router, get_agent_run_repository
from app.agents.repositories import AgentRunRepository
from app.agents.router import AgentRouter
from app.artifacts.dependencies import get_artifact_repository
from app.artifacts.repositories import ArtifactRepository
from app.attachments.dependencies import get_attachment_repository
from app.attachments.repositories import AttachmentRepository, Retriever
from app.api.attachments import AttachmentResponse
from app.conversations.dependencies import (
    get_conversation_repository,
    get_message_repository,
    get_retriever,
)
from app.integrations.embedding.providers import EmbeddingProvider
from app.repositories.conversations import ConversationRepository, MessageRepository
from app.resumes.dependencies import get_student_resume_profile_repository
from app.resumes.repositories import StudentResumeProfileRepository
from app.services.conversations import stream_assistant_reply
from app.services.resume_assistant import RESUME_AGENT_ID, ResumeAssistantService
from app.workspaces.dependencies import (
    get_chat_provider,
    get_current_workspace,
    get_embedding_provider,
    get_session,
)
from app.workspaces.models import AnonymousWorkspace


router = APIRouter(prefix="/api/resume-assistant", tags=["resume-assistant"])


class ResumeProfileResponse(BaseModel):
    current_resume: AttachmentResponse | None


class SetResumeProfileRequest(BaseModel):
    attachment_id: UUID


class StartResumeAnalysisRequest(BaseModel):
    attachment_id: UUID
    target_role: str | None = Field(default=None, max_length=160)
    job_description: str | None = Field(default=None, max_length=12000)
    selected_course_ids: list[UUID] = Field(default_factory=list, max_length=24)


class ResumeArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    conversation_id: UUID
    type: str
    title: str
    content: str
    data: dict
    format: str
    created_at: datetime
    updated_at: datetime


class ResumeAnalysisHistoryResponse(BaseModel):
    run_id: UUID
    conversation_id: UUID
    status: str
    error_message: str | None
    target_role: str | None
    resume_filename: str | None
    summary: str | None
    artifact: ResumeArtifactResponse | None
    created_at: datetime
    updated_at: datetime


def get_resume_assistant_service(
    session: Session = Depends(get_session),
    profiles: StudentResumeProfileRepository = Depends(
        get_student_resume_profile_repository
    ),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
) -> ResumeAssistantService:
    return ResumeAssistantService(
        session,
        profiles,
        attachments,
        conversations,
        agent_runs,
    )


@router.get("/profile", response_model=ResumeProfileResponse)
def get_resume_profile(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> ResumeProfileResponse:
    _require_student(workspace)
    return ResumeProfileResponse(
        current_resume=service.get_current_attachment(workspace.id)
    )


@router.put("/profile", response_model=ResumeProfileResponse)
def set_resume_profile(
    payload: SetResumeProfileRequest,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> ResumeProfileResponse:
    _require_student(workspace)
    return ResumeProfileResponse(
        current_resume=service.set_current_attachment(
            workspace.id, payload.attachment_id
        )
    )


@router.post("/analyses/stream")
async def start_resume_analysis(
    payload: StartResumeAnalysisRequest,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    messages: MessageRepository = Depends(get_message_repository),
    chat_provider=Depends(get_chat_provider),
    agent_router: AgentRouter = Depends(get_agent_router),
    retriever: Retriever = Depends(get_retriever),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
    artifacts: ArtifactRepository = Depends(get_artifact_repository),
) -> StreamingResponse:
    _require_student(workspace)
    conversation, content, input_refs = service.prepare_analysis(
        workspace_id=workspace.id,
        attachment_id=payload.attachment_id,
        target_role=payload.target_role,
        job_description=payload.job_description,
        selected_course_ids=payload.selected_course_ids,
    )
    generator = await stream_assistant_reply(
        conversations=conversations,
        messages=messages,
        chat_provider=chat_provider,
        workspace_id=workspace.id,
        conversation=conversation,
        user_content=content,
        agent_id=RESUME_AGENT_ID,
        role=workspace.role,
        retriever=retriever,
        embedding_provider=embedding_provider,
        attachments=attachments,
        agent_runs=agent_runs,
        artifacts=artifacts,
        router=agent_router,
        selected_attachment_ids=(payload.attachment_id,),
        input_refs=input_refs,
        workflow_id="student-resume-assistant",
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/analyses",
    response_model=list[ResumeAnalysisHistoryResponse],
)
def list_resume_analyses(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> list[ResumeAnalysisHistoryResponse]:
    _require_student(workspace)
    responses = []
    for record in service.list_history(workspace.id):
        attachment = service.attachment_for_record(workspace.id, record)
        artifact = record.artifact
        target_role = _target_role(record.conversation.title, artifact.data if artifact else None)
        summary = record.result_message.content.strip() if record.result_message else None
        if summary and len(summary) > 240:
            summary = f"{summary[:237]}..."
        responses.append(
            ResumeAnalysisHistoryResponse(
                run_id=record.run.id,
                conversation_id=record.conversation.id,
                status=record.run.status,
                error_message=record.run.error_message,
                target_role=target_role,
                resume_filename=attachment.filename if attachment else None,
                summary=summary,
                artifact=(
                    ResumeArtifactResponse.model_validate(artifact)
                    if artifact is not None
                    else None
                ),
                created_at=record.run.created_at,
                updated_at=record.run.updated_at,
            )
        )
    return responses


@router.delete(
    "/analyses/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_resume_analysis(
    run_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    service: ResumeAssistantService = Depends(get_resume_assistant_service),
) -> None:
    _require_student(workspace)
    service.delete_history(workspace.id, run_id)


def _require_student(workspace: AnonymousWorkspace) -> None:
    if workspace.role != "student":
        from app.core.errors import AppError

        raise AppError(
            code="resume_assistant_forbidden",
            message="Resume assistant is only available to student workspaces.",
            status_code=403,
        )


def _target_role(title: str, artifact_data: dict | None) -> str | None:
    if isinstance(artifact_data, dict):
        input_data = artifact_data.get("input")
        if isinstance(input_data, dict):
            value = input_data.get("target_role")
            if isinstance(value, str) and value.strip():
                return value.strip()
    prefix = "简历分析 · "
    value = title.removeprefix(prefix).strip()
    return None if value == "通用优化" else value or None
