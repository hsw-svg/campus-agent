from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.agents.dependencies import get_agent_run_repository
from app.agents.registry import AUTO_AGENT_ID, list_agents
from app.agents.repositories import AgentRunRepository
from app.agents.router import AgentRouter
from app.artifacts.dependencies import get_artifact_repository
from app.artifacts.repositories import ArtifactRepository
from app.attachments.dependencies import get_attachment_repository
from app.attachments.repositories import AttachmentRepository
from app.conversations.dependencies import (
    get_conversation_repository,
    get_message_repository,
    get_retriever,
)
from app.conversations.models import Conversation, Message
from app.repositories.conversations import ConversationRepository, MessageRepository
from app.services.conversations import (
    create_conversation,
    get_owned_conversation,
    stream_assistant_reply,
)
from app.services.routing import classify_message
from app.workspaces.dependencies import get_chat_provider, get_current_workspace, get_embedding_provider
from app.attachments.repositories import Retriever
from app.integrations.embedding.providers import EmbeddingProvider
from app.workspaces.models import AnonymousWorkspace
from app.api.courses import get_owned_course
from app.api.courses import get_course_repository
from app.repositories.courses import CourseRepository

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    agent_id: str | None
    course_id: UUID | None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    agent_id: str | None
    tool_events: list | None
    artifacts: list | None
    created_at: datetime


class ConversationArtifactResponse(BaseModel):
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


class CreateConversationRequest(BaseModel):
    agent_id: str | None = None
    course_id: UUID | None = None


class StreamMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    agent_id: str | None = None
    selected_attachment_ids: list[UUID] | None = None
    selected_artifact_ids: list[UUID] | None = None
    course_id: str | None = Field(default=None, max_length=96)
    workflow_id: str | None = Field(default=None, max_length=96)
    parent_run_id: UUID | None = None
    input_refs: list[str] | None = Field(default=None, max_length=64)


class RouteRequest(BaseModel):
    content: str = Field(min_length=1)
    agent_id: str | None = None
    selected_attachment_ids: list[UUID] | None = None


class RouteCandidateResponse(BaseModel):
    id: str
    name: str
    description: str


class RouteResponse(BaseModel):
    run_id: UUID
    agent: str | None
    agent_id: str | None
    confidence: float
    reason: str
    missing_inputs: list[str]
    selection_source: str
    candidates: list[RouteCandidateResponse]
    candidate_agent_ids: list[str]
    requires_confirmation: bool
    status: str


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def post_conversation(
    payload: CreateConversationRequest,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    courses: CourseRepository = Depends(get_course_repository),
) -> Conversation:
    if payload.course_id is not None:
        get_owned_course(courses, workspace.id, payload.course_id)
    return create_conversation(conversations, workspace.id, workspace.role, payload.agent_id, payload.course_id)


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> list[Conversation]:
    return conversations.list_for_workspace(workspace.id)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> Conversation:
    return get_owned_conversation(conversations, workspace.id, conversation_id)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    messages: MessageRepository = Depends(get_message_repository),
) -> list[Message]:
    get_owned_conversation(conversations, workspace.id, conversation_id)
    return messages.list_for_conversation(workspace.id, conversation_id)


@router.get("/{conversation_id}/artifacts", response_model=list[ConversationArtifactResponse])
def list_conversation_artifacts(
    conversation_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    artifacts: ArtifactRepository = Depends(get_artifact_repository),
) -> list:
    get_owned_conversation(conversations, workspace.id, conversation_id)
    return artifacts.list_for_conversation(workspace.id, conversation_id)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> None:
    conversation = get_owned_conversation(conversations, workspace.id, conversation_id)
    conversations.delete(conversation)


@router.post("/{conversation_id}/route", response_model=RouteResponse)
async def route_message(
    conversation_id: UUID,
    payload: RouteRequest,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    messages: MessageRepository = Depends(get_message_repository),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
    chat_provider=Depends(get_chat_provider),
) -> RouteResponse:
    conversation = get_owned_conversation(conversations, workspace.id, conversation_id)
    agent_id = _normalize_agent_id(payload.agent_id)
    decision = await classify_message(
        router=AgentRouter(chat_provider),
        role=workspace.role,
        conversation=conversation,
        content=payload.content,
        attachments=attachments,
        messages=messages,
        workspace_id=workspace.id,
        manual_agent_id=agent_id,
        selected_attachment_ids=payload.selected_attachment_ids,
    )
    run = agent_runs.create(
        workspace_id=workspace.id,
        conversation_id=conversation.id,
        agent_id=decision.agent,
        selection_source=decision.selection_source,
        confidence=decision.confidence,
        reason=decision.reason,
        missing_inputs=list(decision.missing_inputs),
        candidate_agent_ids=list(decision.candidates),
        selected_attachment_ids=(
            [str(item) for item in payload.selected_attachment_ids]
            if payload.selected_attachment_ids is not None
            else None
        ),
        status="awaiting_confirmation" if decision.requires_confirmation else "routed",
        attempt_count=0,
    )
    return _route_response(workspace.role, decision, run.id, run.status)


@router.post("/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    payload: StreamMessageRequest,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    messages: MessageRepository = Depends(get_message_repository),
    chat_provider=Depends(get_chat_provider),
    retriever: Retriever = Depends(get_retriever),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
    artifacts: ArtifactRepository = Depends(get_artifact_repository),
) -> StreamingResponse:
    conversation = get_owned_conversation(conversations, workspace.id, conversation_id)
    generator = await stream_assistant_reply(
        conversations=conversations,
        messages=messages,
        chat_provider=chat_provider,
        workspace_id=workspace.id,
        conversation=conversation,
        user_content=payload.content,
        agent_id=_normalize_agent_id(payload.agent_id),
        role=workspace.role,
        retriever=retriever,
        embedding_provider=embedding_provider,
        attachments=attachments,
        agent_runs=agent_runs,
        artifacts=artifacts,
        router=AgentRouter(chat_provider),
        selected_attachment_ids=payload.selected_attachment_ids,
        selected_artifact_ids=payload.selected_artifact_ids,
        course_id=payload.course_id,
        workflow_id=payload.workflow_id,
        parent_run_id=payload.parent_run_id,
        input_refs=payload.input_refs,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _normalize_agent_id(agent_id: str | None) -> str | None:
    return None if agent_id in {None, AUTO_AGENT_ID} else agent_id


def _route_response(role: str, decision, run_id: UUID, status: str) -> RouteResponse:
    definitions = {agent.id: agent for agent in list_agents(role)}
    candidates = [
        RouteCandidateResponse(
            id=agent_id,
            name=definitions[agent_id].name,
            description=definitions[agent_id].description,
        )
        for agent_id in decision.candidates
        if agent_id in definitions
    ]
    return RouteResponse(
        run_id=run_id,
        agent=decision.agent,
        agent_id=decision.agent,
        confidence=decision.confidence,
        reason=decision.reason,
        missing_inputs=list(decision.missing_inputs),
        selection_source=decision.selection_source,
        candidates=candidates,
        candidate_agent_ids=list(decision.candidates),
        requires_confirmation=decision.requires_confirmation,
        status=status,
    )
