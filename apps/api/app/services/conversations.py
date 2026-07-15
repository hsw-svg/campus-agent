from collections.abc import AsyncIterator
from uuid import UUID

from app.agents.registry import is_agent_available_for_role
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
) -> AsyncIterator[str]:
    """Persist the user turn, stream the assistant reply, and persist the result.

    A failure from the model surfaces as an ``error`` event while the user
    message and the conversation stay intact so the turn can be retried.
    """

    resolved_agent = agent_id if agent_id is not None else conversation.agent_id
    if resolved_agent is not None and not is_agent_available_for_role(role, resolved_agent):
        raise AppError(
            code="agent_not_available",
            message="The requested agent is not available for this role.",
            status_code=400,
        )

    user_message = messages.add(
        workspace_id=workspace_id,
        conversation_id=conversation.id,
        role="user",
        content=user_content,
    )
    if conversation.title == DEFAULT_TITLE:
        conversations.rename(conversation, derive_title(user_content))
    if agent_id is not None and agent_id != conversation.agent_id:
        conversations.set_agent(conversation, agent_id)

    history = _history_payload(
        messages.list_for_conversation(workspace_id, conversation.id)
    )

    async def generator() -> AsyncIterator[str]:
        yield stream_event(
            "message_start",
            {
                "conversation_id": str(conversation.id),
                "user_message_id": str(user_message.id),
                "agent_id": resolved_agent,
            },
        )

        if not chat_provider.is_configured:
            yield stream_event(
                "error",
                {
                    "code": "chat_model_unconfigured",
                    "message": "The chat model is not configured. Add credentials and retry.",
                    "retryable": True,
                },
            )
            return

        collected: list[str] = []
        try:
            async for delta in chat_provider.stream_reply(history):
                collected.append(delta)
                yield stream_event("delta", {"text": delta})
        except Exception as error:  # noqa: BLE001 - surfaced as a retryable stream error
            yield stream_event(
                "error",
                {
                    "code": "chat_stream_failed",
                    "message": "The chat model did not complete the response.",
                    "detail": str(error),
                    "retryable": True,
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
        )
        conversations.touch(conversation)
        yield stream_event(
            "done",
            {
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id),
                "agent_id": resolved_agent,
            },
        )

    return generator()
