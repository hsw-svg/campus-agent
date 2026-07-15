from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

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
from app.workspaces.dependencies import get_chat_provider, get_current_workspace, get_embedding_provider
from app.attachments.repositories import Retriever
from app.integrations.embedding.providers import EmbeddingProvider
from app.workspaces.models import AnonymousWorkspace

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    agent_id: str | None
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


class CreateConversationRequest(BaseModel):
    agent_id: str | None = None


class StreamMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    agent_id: str | None = None


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def post_conversation(
    payload: CreateConversationRequest,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> Conversation:
    return create_conversation(conversations, workspace.id, workspace.role, payload.agent_id)


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


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
) -> None:
    conversation = get_owned_conversation(conversations, workspace.id, conversation_id)
    conversations.delete(conversation)


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
) -> StreamingResponse:
    conversation = get_owned_conversation(conversations, workspace.id, conversation_id)
    generator = await stream_assistant_reply(
        conversations=conversations,
        messages=messages,
        chat_provider=chat_provider,
        workspace_id=workspace.id,
        conversation=conversation,
        user_content=payload.content,
        agent_id=payload.agent_id,
        role=workspace.role,
        retriever=retriever,
        embedding_provider=embedding_provider,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
