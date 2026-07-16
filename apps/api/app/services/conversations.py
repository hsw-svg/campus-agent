from collections.abc import AsyncIterator
from uuid import UUID

from app.agents.registry import is_agent_available_for_role
from app.agents.models import AgentRun
from app.agents.repositories import AgentRunRepository
from app.agents.router import AgentRouter, RouteDecision
from app.attachments.repositories import AttachmentRepository, Retriever
from app.integrations.embedding.providers import EmbeddingProvider
from app.services.attachments import retrieve_context
from app.services.routing import classify_message
from app.conversations.models import Conversation, Message
from app.conversations.streaming import stream_event
from app.core.errors import AppError
from app.integrations.llm.providers import ChatProvider
from app.repositories.conversations import ConversationRepository, MessageRepository

# The context sent to the chat model is capped so a long history does not grow
# the prompt without bound; the shell still shows the full stored transcript.
MAX_CONTEXT_MESSAGES = 20

DEFAULT_TITLE = "新对话"
TITLE_MAX_LENGTH = 30


def create_conversation(
    conversations: ConversationRepository,
    workspace_id: UUID,
    role: str,
    agent_id: str | None,
) -> Conversation:
    if agent_id is not None and not is_agent_available_for_role(role, agent_id):
        raise AppError(
            code="agent_not_available",
            message="The requested agent is not available for this role.",
            status_code=400,
        )
    return conversations.create(workspace_id=workspace_id, title=DEFAULT_TITLE, agent_id=agent_id)


def get_owned_conversation(
    conversations: ConversationRepository,
    workspace_id: UUID,
    conversation_id: UUID,
) -> Conversation:
    conversation = conversations.get(workspace_id, conversation_id)
    if conversation is None:
        raise AppError(
            code="conversation_not_found",
            message="Conversation was not found.",
            status_code=404,
        )
    return conversation


def derive_title(content: str) -> str:
    """Use the first user turn as a readable conversation title."""

    condensed = " ".join(content.split())
    if not condensed:
        return DEFAULT_TITLE
    if len(condensed) <= TITLE_MAX_LENGTH:
        return condensed
    return condensed[:TITLE_MAX_LENGTH] + "…"


def _history_payload(messages: list[Message]) -> list[dict[str, str]]:
    trimmed = messages[-MAX_CONTEXT_MESSAGES:]
    return [{"role": message.role, "content": message.content} for message in trimmed]


async def stream_assistant_reply(
    *,
    conversations: ConversationRepository,
    messages: MessageRepository,
    chat_provider: ChatProvider,
    workspace_id: UUID,
    conversation: Conversation,
    user_content: str,
    agent_id: str | None,
    role: str,
    retriever: Retriever | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    attachments: AttachmentRepository | None = None,
    agent_runs: AgentRunRepository | None = None,
    router: AgentRouter | None = None,
    existing_run: AgentRun | None = None,
    existing_user_message: Message | None = None,
) -> AsyncIterator[str]:
    """Persist the user turn, stream the assistant reply, and persist the result.

    A failure from the model surfaces as an ``error`` event while the user
    message and the conversation stay intact so the turn can be retried.
    """

    route_decision = RouteDecision(
        agent=agent_id if agent_id is not None else conversation.agent_id,
        confidence=1.0 if agent_id is not None or conversation.agent_id is not None else 0.0,
        reason=(
            "沿用当前选择的智能体。"
            if agent_id is not None or conversation.agent_id is not None
            else "未执行阶段5路由。"
        ),
        selection_source="manual" if agent_id is not None or conversation.agent_id is not None else "fallback",
    )
    if router is not None and attachments is not None and agent_runs is not None:
        route_decision = await classify_message(
            router=router,
            role=role,
            conversation=conversation,
            content=user_content,
            attachments=attachments,
            messages=messages,
            workspace_id=workspace_id,
            manual_agent_id=agent_id if agent_id is not None else conversation.agent_id,
        )

    resolved_agent = route_decision.agent
    if resolved_agent is not None and not is_agent_available_for_role(role, resolved_agent):
        raise AppError(
            code="agent_not_available",
            message="The requested agent is not available for this role.",
            status_code=400,
        )

    user_message = existing_user_message or messages.add(
        workspace_id=workspace_id,
        conversation_id=conversation.id,
        role="user",
        content=user_content,
    )
    if conversation.title == DEFAULT_TITLE:
        conversations.rename(conversation, derive_title(user_content))
    if agent_id is not None and agent_id != conversation.agent_id:
        conversations.set_agent(conversation, agent_id)

    run: AgentRun | None = None
    if agent_runs is not None:
        run_values = {
            "workspace_id": workspace_id,
            "conversation_id": conversation.id,
            "message_id": user_message.id,
            "agent_id": resolved_agent,
            "selection_source": route_decision.selection_source,
            "confidence": route_decision.confidence,
            "reason": route_decision.reason,
            "missing_inputs": list(route_decision.missing_inputs),
            "candidate_agent_ids": list(route_decision.candidates),
            "status": "awaiting_confirmation"
            if route_decision.requires_confirmation
            else "running",
            "error_code": None,
            "error_message": None,
            "artifact_status": "none",
            "attempt_count": (existing_run.attempt_count + 1) if existing_run else 1,
        }
        if existing_run is None:
            run = agent_runs.create(**run_values)
        else:
            run = agent_runs.update(existing_run, **run_values)

    sources: list[dict[str, str | int | None]] = []
    if retriever is not None and embedding_provider is not None:
        chunks = retrieve_context(
            retriever=retriever,
            embedding_provider=embedding_provider,
            workspace_id=workspace_id,
            conversation_id=conversation.id,
            query=user_content,
        )
        sources = [
            {
                "attachment_id": str(chunk.attachment_id),
                "chunk_id": str(chunk.id),
                "filename": chunk.attachment.filename if chunk.attachment else None,
                "page_number": chunk.page_number,
                "excerpt": chunk.content[:240],
            }
            for chunk in chunks
        ]
    history = _history_payload(messages.list_for_conversation(workspace_id, conversation.id))
    if sources:
        context = "\n\n".join(
            f"[{source['filename']}] {source['excerpt']}" for source in sources
        )
        history.insert(
            0,
            {
                "role": "system",
                "content": "仅使用以下当前角色工作空间资料回答；资料不足时明确说明。\n" + context,
            },
        )

    async def generator() -> AsyncIterator[str]:
        yield stream_event(
            "message_start",
            {
                "conversation_id": str(conversation.id),
                "user_message_id": str(user_message.id),
                "agent_id": resolved_agent,
                "agent_name": _agent_name(role, resolved_agent),
                "selection_source": route_decision.selection_source,
                "confidence": route_decision.confidence,
                "run_id": str(run.id) if run else None,
            },
        )
        if route_decision.requires_confirmation:
            if run is not None and agent_runs is not None:
                agent_runs.update(run, status="awaiting_confirmation")
            yield stream_event(
                "tool_status",
                {
                    "status": "route_confirmation_required",
                    "run_id": str(run.id) if run else None,
                    "candidates": list(route_decision.candidates),
                    "reason": route_decision.reason,
                },
            )
            yield stream_event(
                "error",
                {
                    "code": "route_confirmation_required",
                    "message": "请确认要调用的智能体后再继续。",
                    "retryable": False,
                    "run_id": str(run.id) if run else None,
                    "candidates": list(route_decision.candidates),
                },
            )
            return

        if route_decision.missing_inputs:
            if run is not None and agent_runs is not None:
                agent_runs.update(
                    run,
                    status="needs_input",
                    error_code="agent_input_incomplete",
                    error_message="目标智能体缺少必要输入。",
                )
            yield stream_event(
                "error",
                {
                    "code": "agent_input_incomplete",
                    "message": "目标智能体缺少必要输入。",
                    "missing_inputs": list(route_decision.missing_inputs),
                    "retryable": False,
                    "run_id": str(run.id) if run else None,
                },
            )
            return

        yield stream_event(
            "tool_status",
            {
                "status": "agent_routed" if resolved_agent else "generic_fallback",
                "agent_id": resolved_agent,
                "agent_name": _agent_name(role, resolved_agent),
                "selection_source": route_decision.selection_source,
                "confidence": route_decision.confidence,
                "run_id": str(run.id) if run else None,
            },
        )
        if sources:
            yield stream_event("tool_status", {"status": "retrieved", "count": len(sources)})
            yield stream_event("artifact", {"type": "sources", "sources": sources})

        if not chat_provider.is_configured:
            if run is not None and agent_runs is not None:
                agent_runs.update(
                    run,
                    status="failed",
                    error_code="chat_model_unconfigured",
                    error_message="The chat model is not configured.",
                )
            yield stream_event(
                "error",
                {
                    "code": "chat_model_unconfigured",
                    "message": "The chat model is not configured. Add credentials and retry.",
                    "retryable": True,
                    "run_id": str(run.id) if run else None,
                },
            )
            return

        collected: list[str] = []
        try:
            async for delta in chat_provider.stream_reply(history):
                collected.append(delta)
                yield stream_event("delta", {"text": delta})
        except Exception as error:  # noqa: BLE001 - surfaced as a retryable stream error
            if run is not None and agent_runs is not None:
                agent_runs.update(
                    run,
                    status="failed",
                    error_code="chat_stream_failed",
                    error_message=str(error),
                )
            yield stream_event(
                "error",
                {
                    "code": "chat_stream_failed",
                    "message": "The chat model did not complete the response.",
                    "detail": str(error),
                    "retryable": True,
                    "run_id": str(run.id) if run else None,
                },
            )
            return

        assistant_content = "".join(collected)
        assistant_message = messages.add(
            workspace_id=workspace_id,
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_content,
            agent_id=resolved_agent,
            artifacts=[{"type": "sources", "sources": sources}] if sources else None,
        )
        conversations.touch(conversation)
        if run is not None and agent_runs is not None:
            agent_runs.update(
                run,
                status="completed",
                result_message_id=assistant_message.id,
            )
        yield stream_event(
            "done",
            {
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id),
                "agent_id": resolved_agent,
                "run_id": str(run.id) if run else None,
            },
        )

    return generator()


def _agent_name(role: str, agent_id: str | None) -> str | None:
    if agent_id is None:
        return None
    from app.agents.registry import list_agents

    return next((agent.name for agent in list_agents(role) if agent.id == agent_id), None)
