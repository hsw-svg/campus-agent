from uuid import UUID

from app.attachments.models import Attachment, MaterialChunk
from app.attachments.parsing import parse_document, split_into_chunks
from app.attachments.repositories import AttachmentRepository, Retriever
from app.core.errors import AppError
from app.integrations.embedding.providers import EmbeddingProvider


def process_attachment(
    *,
    attachment: Attachment,
    content: bytes,
    repository: AttachmentRepository,
    embedding_provider: EmbeddingProvider,
) -> Attachment:
    repository.update(attachment, status="parsing", status_message=None)
    try:
        parsed = parse_document(attachment.filename, content)
        chunks = split_into_chunks(parsed.text)
        embeddings: list[list[float] | None] = [None] * len(chunks)
        status = "indexed"
        status_message = parsed.warning
        if chunks and embedding_provider.is_configured:
            try:
                values = embedding_provider.embed(chunks)
                if len(values) != len(chunks):
                    raise ValueError("embedding response count does not match chunk count")
                embeddings = values
            except Exception as error:  # noqa: BLE001 - keyword retrieval remains usable
                status = "degraded"
                status_message = f"向量索引失败，已降级为关键词检索：{error}"
        elif chunks:
            status = "degraded"
            status_message = status_message or "Embedding 未配置，已降级为关键词检索。"
        elif parsed.warning:
            status = "degraded"
        else:
            status = "failed"
            status_message = "文件中没有可索引的文本。"

        material_chunks = [
            MaterialChunk(
                attachment_id=attachment.id,
                workspace_id=attachment.workspace_id,
                conversation_id=attachment.conversation_id,
                chunk_index=index,
                content=chunk,
                embedding=embeddings[index],
            )
            for index, chunk in enumerate(chunks)
        ]
        if material_chunks:
            repository.add_chunks(material_chunks)
        return repository.update(
            attachment,
            status=status,
            status_message=status_message,
            extracted_chars=len(parsed.text),
        )
    except AppError as error:
        return repository.update(
            attachment,
            status="failed",
            status_message=error.message,
        )
    except Exception as error:  # noqa: BLE001 - preserve a retryable attachment record
        return repository.update(
            attachment,
            status="failed",
            status_message=f"文件解析失败：{error}",
        )


def retrieve_context(
    *,
    retriever: Retriever,
    embedding_provider: EmbeddingProvider,
    workspace_id: UUID,
    conversation_id: UUID,
    query: str,
) -> list[MaterialChunk]:
    query_embedding: list[float] | None = None
    if embedding_provider.is_configured:
        try:
            query_embedding = embedding_provider.embed([query])[0]
        except Exception:
            query_embedding = None
    return retriever.retrieve(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query=query,
        query_embedding=query_embedding,
    )
