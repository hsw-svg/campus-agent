from collections.abc import Sequence
from uuid import UUID

from app.agents.router import AgentRouter, RouteAttachment, RouteContext, RouteDecision
from app.attachments.models import Attachment
from app.attachments.repositories import AttachmentRepository
from app.conversations.models import Conversation
from app.repositories.conversations import MessageRepository
from app.courses.context import CourseLearningContext


def make_route_context(
    *,
    conversation: Conversation,
    role: str,
    content: str,
    attachments: AttachmentRepository,
    messages: MessageRepository,
    workspace_id,
    selected_attachment_ids: Sequence[UUID] | None = None,
    course_context: CourseLearningContext | None = None,
) -> RouteContext:
    selected = (
        attachments.list_selected_for_conversation(
            workspace_id, conversation.id, selected_attachment_ids, conversation.course_id
        )
        if selected_attachment_ids is not None or conversation.course_id is not None
        else []
    )
    attachment_facts = tuple(
        _attachment_fact(attachment)
        for attachment in selected
    )
    workspace_attachment_facts = tuple(
        _attachment_fact(attachment)
        for attachment in attachments.list_for_conversation(workspace_id, conversation.id, conversation.course_id)
    )
    recent_messages = tuple(
        {
            "role": message.role,
            "content": message.content,
            "agent_id": message.agent_id,
        }
        for message in messages.list_for_conversation(workspace_id, conversation.id)[-6:]
    )
    return RouteContext(
        role=role,
        content=content,
        attachments=attachment_facts,
        workspace_attachments=workspace_attachment_facts,
        selected_attachment_ids=tuple(str(attachment.id) for attachment in selected),
        recent_messages=recent_messages,
        conversation_agent_id=conversation.agent_id,
        course=course_context,
    )


def _attachment_fact(attachment: Attachment) -> RouteAttachment:
    chunks = sorted(attachment.chunks, key=lambda chunk: chunk.chunk_index)
    text = "\n".join(chunk.content for chunk in chunks)[:2400]
    headers: list[str] = []
    for line in text.splitlines()[:3]:
        if "|" in line:
            headers.extend(part.strip() for part in line.split("|") if part.strip())
        elif "," in line:
            headers.extend(part.strip() for part in line.split(",") if part.strip())
        elif line.strip():
            headers.append(line.strip())
    return RouteAttachment(
        filename=attachment.filename,
        content_type=attachment.content_type,
        headers=tuple(headers[:24]),
        text_excerpt=text,
        status=attachment.status,
    )


async def classify_message(
    *,
    router: AgentRouter,
    role: str,
    conversation: Conversation,
    content: str,
    attachments: AttachmentRepository,
    messages: MessageRepository,
    workspace_id,
    manual_agent_id: str | None = None,
    selected_attachment_ids: Sequence[UUID] | None = None,
    course_context: CourseLearningContext | None = None,
) -> RouteDecision:
    context = make_route_context(
        conversation=conversation,
        role=role,
        content=content,
        attachments=attachments,
        messages=messages,
        workspace_id=workspace_id,
        selected_attachment_ids=selected_attachment_ids,
        course_context=course_context,
    )
    return await router.route(context, manual_agent_id=manual_agent_id)
