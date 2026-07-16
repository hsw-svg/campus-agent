from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agents.dependencies import get_agent_run_repository
from app.agents.repositories import AgentRunRepository
from app.agents.router import AgentRouter
from app.attachments.dependencies import get_attachment_repository
from app.attachments.repositories import AttachmentRepository, Retriever
from app.conversations.dependencies import (
    get_conversation_repository,
    get_message_repository,
    get_retriever,
)
from app.conversations.models import Message
from app.integrations.embedding.providers import EmbeddingProvider
from app.repositories.conversations import ConversationRepository, MessageRepository
from app.services.conversations import get_owned_conversation, stream_assistant_reply
from app.workspaces.dependencies import get_chat_provider, get_current_workspace, get_embedding_provider
from app.workspaces.models import AnonymousWorkspace

router = APIRouter(prefix="/api/agent-runs", tags=["agent-runs"])


@router.post("/{run_id}/retry")
async def retry_agent_run(
    run_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    messages: MessageRepository = Depends(get_message_repository),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
    chat_provider=Depends(get_chat_provider),
    retriever: Retriever = Depends(get_retriever),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> StreamingResponse:
    run = agent_runs.get(workspace.id, run_id)
    if run is None:
        from app.core.errors import AppError

        raise AppError(
            code="agent_run_not_found",
            message="Agent run was not found.",
            status_code=404,
        )
    if run.status not in {"failed", "needs_input"}:
        from app.core.errors import AppError

        raise AppError(
            code="agent_run_not_retryable",
            message="Only failed or incomplete agent runs can be retried.",
            status_code=409,
        )
    if run.message_id is None:
        from app.core.errors import AppError

        raise AppError(
            code="agent_run_not_retryable",
            message="This routing-only run has no message to retry.",
            status_code=409,
        )
    conversation = get_owned_conversation(conversations, workspace.id, run.conversation_id)
    message = messages.get(workspace.id, run.message_id)
    if message is None:
        from app.core.errors import AppError

        raise AppError(
            code="agent_run_not_found",
            message="The message for this agent run was not found.",
            status_code=404,
        )
    generator = await stream_assistant_reply(
        conversations=conversations,
        messages=messages,
        chat_provider=chat_provider,
        workspace_id=workspace.id,
        conversation=conversation,
        user_content=message.content,
        agent_id=run.agent_id if run.selection_source == "manual" else None,
        role=workspace.role,
        retriever=retriever,
        embedding_provider=embedding_provider,
        attachments=attachments,
        agent_runs=agent_runs,
        router=AgentRouter(chat_provider),
        existing_run=run,
        existing_user_message=message,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
