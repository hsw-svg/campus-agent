from collections.abc import AsyncIterator, Sequence
from uuid import UUID

from app.agents.registry import is_agent_available_for_role
from app.agents.contracts import AgentRequest
from app.agents.executors.registry import AgentExecutorRegistry
from app.agents.context import ContextBuilder
from app.agents.specs import AgentSpec, get_agent_spec
from app.agents.models import AgentRun
from app.agents.repositories import AgentRunRepository
from app.agents.router import AgentRouter, RouteDecision
from app.artifacts.repositories import ArtifactRepository
from app.attachments.repositories import AttachmentRepository, Retriever
from app.integrations.embedding.providers import EmbeddingProvider
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
    artifacts: ArtifactRepository | None = None,
    router: AgentRouter | None = None,
    selected_attachment_ids: Sequence[UUID] | None = None,
    selected_artifact_ids: Sequence[UUID] | None = None,
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
            manual_agent_id=agent_id,
            selected_attachment_ids=selected_attachment_ids,
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
            "selected_attachment_ids": (
                [str(item) for item in selected_attachment_ids]
                if selected_attachment_ids is not None
                else None
            ),
            "selected_artifact_ids": (
                [str(item) for item in selected_artifact_ids]
                if selected_artifact_ids is not None
                else None
            ),
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
        yield stream_event(
            "route_decision",
            {
                "agent_id": resolved_agent,
                "agent_name": _agent_name(role, resolved_agent),
                "confidence": route_decision.confidence,
                "reason": route_decision.reason,
                "selection_source": route_decision.selection_source,
                "missing_inputs": list(route_decision.missing_inputs),
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

        try:
            if retriever is None or embedding_provider is None or attachments is None:
                raise AppError(
                    code="agent_context_unavailable",
                    message="The agent context is not available.",
                    status_code=500,
                )
            context_builder = ContextBuilder(
                attachments=attachments,
                messages=messages,
                retriever=retriever,
                embedding_provider=embedding_provider,
                artifacts=artifacts,
            )
            context, normalized_attachment_ids = context_builder.build(
                workspace_id=workspace_id,
                conversation=conversation,
                role=role,
                agent_id=resolved_agent or "generic_chat",
                content=user_content,
                selected_attachment_ids=selected_attachment_ids,
                selected_artifact_ids=selected_artifact_ids or (),
            )
            if run is not None and agent_runs is not None:
                agent_runs.update(
                    run,
                    selected_attachment_ids=[str(item) for item in normalized_attachment_ids],
                )
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
            request = AgentRequest(
                workspace_id=workspace_id,
                conversation_id=conversation.id,
                role=role,
                agent_id=resolved_agent or "generic_chat",
                content=user_content,
                selected_attachment_ids=normalized_attachment_ids,
                selected_artifact_ids=tuple(selected_artifact_ids or ()),
                context=context,
            )
            spec = get_agent_spec(role, resolved_agent) if resolved_agent else None
            if spec is None:
                spec = AgentSpec(
                    id=resolved_agent or "generic_chat",
                    role=role,
                    name="通用对话",
                    description="当前角色的通用对话能力",
                    system_prompt="你是校园智能助手。只使用当前允许的资料回答，资料不足时明确说明。",
                    executor_id="generic_chat",
                )
            executor = AgentExecutorRegistry(chat_provider).resolve(spec)
            result = await executor.execute(request)
            source_payload = [
                {
                    "attachment_id": str(source.attachment_id),
                    "filename": source.filename,
                    "page_number": source.page_number,
                    "excerpt": source.excerpt,
                }
                for source in result.citations
            ]
            if source_payload:
                yield stream_event(
                    "tool_status",
                    {
                        "status": "retrieved",
                        "count": len(source_payload),
                        "agent_id": resolved_agent,
                    },
                )
                yield stream_event("artifact", {"type": "sources", "sources": source_payload})
        except Exception as error:  # noqa: BLE001 - surfaced as a retryable stream error
            if isinstance(error, AppError):
                error_code = error.code
                error_message = error.message
                details = error.details
                retryable = error.status_code != 422
                status = "needs_input" if error.status_code == 422 else "failed"
            elif str(error) == "chat_model_unconfigured":
                error_code = "chat_model_unconfigured"
                error_message = "The chat model is not configured. Add credentials and retry."
                details = None
                retryable = True
                status = "failed"
            else:
                error_code = "chat_stream_failed"
                error_message = "The chat model did not complete the response."
                details = str(error)
                retryable = True
                status = "failed"
            if run is not None and agent_runs is not None:
                agent_runs.update(
                    run,
                    status=status,
                    error_code=error_code,
                    error_message=error_message,
                )
            yield stream_event(
                "error",
                {
                    "code": error_code,
                    "message": error_message,
                    "details": details,
                    "retryable": retryable,
                    "run_id": str(run.id) if run else None,
                },
            )
            return

        artifact_id = None
        artifact_payload = None
        message_artifacts = None
        if result.artifact is not None and artifacts is not None:
            artifact = artifacts.create(
                workspace_id=workspace_id,
                conversation_id=conversation.id,
                type=result.artifact.type,
                title=result.artifact.title,
                content=result.artifact.content,
                data=result.artifact.data,
                format=result.artifact.format,
            )
            artifact_id = artifact.id
            artifact_payload = {
                "type": result.artifact.type,
                "artifact_id": str(artifact.id),
                "title": artifact.title,
                "data": result.artifact.data,
            }
            message_artifacts = [
                {"type": result.artifact.type, "artifact_id": str(artifact.id), "title": artifact.title}
            ]
        assistant_message = messages.add(
            workspace_id=workspace_id,
            conversation_id=conversation.id,
            role="assistant",
            content=result.text,
            agent_id=resolved_agent,
            artifacts=message_artifacts
            or ([{"type": "sources", "sources": source_payload}] if source_payload else None),
        )
        conversations.touch(conversation)
        if run is not None and agent_runs is not None:
            agent_runs.update(
                run,
                status="completed",
                result_message_id=assistant_message.id,
                artifact_id=artifact_id,
                artifact_status="completed" if artifact_id else "none",
            )
        yield stream_event("delta", {"text": result.text})
        if artifact_payload is not None:
            yield stream_event("artifact", artifact_payload)
        yield stream_event(
            "done",
            {
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id),
                "agent_id": resolved_agent,
                "run_id": str(run.id) if run else None,
                "artifact_id": str(artifact_id) if artifact_id else None,
            },
        )

    return generator()


def _agent_name(role: str, agent_id: str | None) -> str | None:
    if agent_id is None:
        return None
    from app.agents.registry import list_agents

    return next((agent.name for agent in list_agents(role) if agent.id == agent_id), None)
