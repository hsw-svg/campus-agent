"""Agent-specific context selection and prompt assembly."""

from collections.abc import Sequence
from uuid import UUID

from app.agents.contracts import AgentContext, ContextSource
from app.agents.specs import AgentSpec, get_agent_spec
from app.artifacts.repositories import ArtifactRepository
from app.attachments.repositories import AttachmentRepository, Retriever
from app.attachments.policies import is_learning_analysis_material
from app.conversations.models import Conversation, Message
from app.core.errors import AppError
from app.integrations.embedding.providers import EmbeddingProvider
from app.repositories.conversations import MessageRepository
from app.services.attachments import retrieve_context


class ContextBuilder:
    """Build the smallest context allowed by the selected AgentSpec."""

    def __init__(
        self,
        *,
        attachments: AttachmentRepository,
        messages: MessageRepository,
        retriever: Retriever,
        embedding_provider: EmbeddingProvider,
        artifacts: ArtifactRepository | None = None,
    ) -> None:
        self.attachments = attachments
        self.messages = messages
        self.retriever = retriever
        self.embedding_provider = embedding_provider
        self.artifacts = artifacts

    def build(
        self,
        *,
        workspace_id: UUID,
        conversation: Conversation,
        role: str,
        agent_id: str,
        content: str,
        selected_attachment_ids: Sequence[UUID] | None = None,
        selected_artifact_ids: Sequence[UUID] = (),
    ) -> tuple[AgentContext, tuple[UUID, ...]]:
        spec = get_agent_spec(role, agent_id) or AgentSpec(
            id=agent_id,
            role=role,
            name="通用对话",
            description="当前角色的通用对话能力",
            system_prompt="你是校园智能助手。只使用当前允许的资料回答，资料不足时明确说明。",
            executor_id="generic_chat",
        )
        selected = (
            self.attachments.list_selected_for_conversation(
                workspace_id, conversation.id, selected_attachment_ids
            )
            if selected_attachment_ids is not None or not spec.context_policy.requires_explicit_attachments
            else []
        )
        selected_ids = tuple(attachment.id for attachment in selected)
        if spec.context_policy.requires_explicit_attachments and not selected:
            raise AppError(
                code="agent_input_incomplete",
                message="请选择目标智能体需要的资料。",
                status_code=422,
                details={"missing_inputs": ["用户明确选择的附件"]},
            )

        if agent_id == "learning_analysis":
            chunks = self.attachments.list_chunks_for_attachments(
                workspace_id, conversation.id, selected_ids
            )
        else:
            chunks = retrieve_context(
                retriever=self.retriever,
                embedding_provider=self.embedding_provider,
                workspace_id=workspace_id,
                conversation_id=conversation.id,
                query=content,
                agent_id=agent_id,
                attachment_ids=selected_ids,
            )
        if spec.context_policy.exclude_learning_details:
            chunks = [chunk for chunk in chunks if not is_learning_analysis_material(chunk)]
        sources = tuple(
            ContextSource(
                attachment_id=chunk.attachment_id,
                filename=chunk.attachment.filename if chunk.attachment else "",
                excerpt=chunk.content[:240],
                page_number=chunk.page_number,
            )
            for chunk in chunks
            if chunk.attachment is not None
        )
        history = self._history(
            workspace_id=workspace_id,
            conversation_id=conversation.id,
            agent_id=agent_id,
        )
        selected_artifacts = (
            self.artifacts.list_selected_for_conversation(
                workspace_id, conversation.id, tuple(selected_artifact_ids)
            )
            if self.artifacts is not None
            else []
        )
        messages = [
            {"role": "system", "content": spec.system_prompt},
            *history,
        ]
        if selected_artifacts:
            artifact_text = "\n\n".join(
                f"[已选择成果：{artifact.title}]\n{artifact.content}"
                for artifact in selected_artifacts
            )
            messages[0] = {
                "role": "system",
                "content": messages[0]["content"]
                + "\n\n仅使用以下已选择的成果：\n"
                + artifact_text,
            }
        if sources:
            source_text = "\n\n".join(
                f"[{source.filename}] {source.excerpt}" for source in sources
            )
            messages[0] = {
                "role": "system",
                "content": messages[0]["content"]
                + "\n\n仅使用以下当前智能体允许的资料回答；资料不足时明确说明。\n"
                + source_text,
            }
        attachment_chunks = self.attachments.list_chunks_for_attachments(
            workspace_id, conversation.id, selected_ids
        )
        return (
            AgentContext(
                messages=tuple(messages),
                sources=sources,
                attachment_text="\n".join(chunk.content for chunk in attachment_chunks),
                attachment_filenames=tuple(attachment.filename for attachment in selected),
            ),
            selected_ids,
        )

    def _history(
        self, *, workspace_id: UUID, conversation_id: UUID, agent_id: str
    ) -> list[dict[str, str]]:
        messages: list[Message] = self.messages.list_for_conversation(
            workspace_id, conversation_id
        )[-20:]
        return [
            {"role": message.role, "content": message.content}
            for message in messages
            if agent_id == "learning_analysis" or message.agent_id != "learning_analysis"
        ]
