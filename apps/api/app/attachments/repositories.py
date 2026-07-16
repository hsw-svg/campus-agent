from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.attachments.models import Attachment, MaterialChunk


class AttachmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values) -> Attachment:
        attachment = Attachment(**values)
        self.session.add(attachment)
        self.session.commit()
        self.session.refresh(attachment)
        return attachment

    def get(self, workspace_id: UUID, attachment_id: UUID) -> Attachment | None:
        return self.session.scalar(
            select(Attachment).where(
                Attachment.id == attachment_id, Attachment.workspace_id == workspace_id
            )
        )

    def list_for_conversation(self, workspace_id: UUID, conversation_id: UUID) -> list[Attachment]:
        return list(
            self.session.scalars(
                select(Attachment)
                .where(
                    Attachment.workspace_id == workspace_id,
                    (Attachment.conversation_id == conversation_id)
                    | (Attachment.conversation_id.is_(None)),
                )
                .order_by(Attachment.created_at)
            )
        )

    def list_chunks_for_conversation(self, workspace_id: UUID, conversation_id: UUID) -> list[MaterialChunk]:
        return list(
            self.session.scalars(
                select(MaterialChunk)
                .join(Attachment, MaterialChunk.attachment_id == Attachment.id)
                .where(
                    MaterialChunk.workspace_id == workspace_id,
                    Attachment.workspace_id == workspace_id,
                    (MaterialChunk.conversation_id == conversation_id)
                    | (MaterialChunk.conversation_id.is_(None)),
                )
                .order_by(Attachment.created_at, MaterialChunk.chunk_index)
            )
        )

    def update(self, attachment: Attachment, **values) -> Attachment:
        for key, value in values.items():
            setattr(attachment, key, value)
        self.session.commit()
        self.session.refresh(attachment)
        return attachment

    def add_chunks(self, chunks: list[MaterialChunk]) -> None:
        self.session.add_all(chunks)
        self.session.commit()


class Retriever:
    """Workspace-first retrieval with a deterministic keyword fallback."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def retrieve(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        query: str,
        limit: int = 5,
        query_embedding: list[float] | None = None,
    ) -> list[MaterialChunk]:
        chunks = list(
            self.session.scalars(
                select(MaterialChunk).where(
                    MaterialChunk.workspace_id == workspace_id,
                    (
                        (MaterialChunk.conversation_id == conversation_id)
                        | (MaterialChunk.conversation_id.is_(None))
                    ),
                )
            )
        )
        normalized_query = query.strip().lower()
        terms = {term.lower() for term in query.split() if len(term.strip()) > 1}
        if len(normalized_query) > 1:
            terms.add(normalized_query)

        def keyword_score(chunk: MaterialChunk) -> tuple[int, int]:
            lowered = chunk.content.lower()
            return (sum(lowered.count(term) for term in terms), -chunk.chunk_index)

        if query_embedding:
            ranked = sorted(
                chunks,
                key=lambda chunk: (_cosine_similarity(query_embedding, chunk.embedding or []), keyword_score(chunk)),
                reverse=True,
            )
            matches = [
                chunk
                for chunk in ranked
                if keyword_score(chunk)[0] > 0
                or _cosine_similarity(query_embedding, chunk.embedding or []) >= 0.2
            ]
        else:
            ranked = sorted(chunks, key=keyword_score, reverse=True)
            matches = [chunk for chunk in ranked if keyword_score(chunk)[0] > 0]
        return matches[:limit]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
