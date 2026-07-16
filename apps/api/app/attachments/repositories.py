from collections.abc import Sequence
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.attachments.models import Attachment, MaterialChunk
from app.attachments.policies import is_learning_analysis_material
from app.core.errors import AppError


class AttachmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values) -> Attachment:
        attachment = Attachment(**values)
        self.session.add(attachment)
        self._commit()
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

    def list_current_for_conversation(self, workspace_id: UUID, conversation_id: UUID) -> list[Attachment]:
        return list(
            self.session.scalars(
                select(Attachment)
                .where(
                    Attachment.workspace_id == workspace_id,
                    Attachment.conversation_id == conversation_id,
                )
                .order_by(Attachment.created_at)
            )
        )

    def list_workspace_for_conversation(
        self, workspace_id: UUID, conversation_id: UUID
    ) -> list[Attachment]:
        return list(
            self.session.scalars(
                select(Attachment)
                .where(
                    Attachment.workspace_id == workspace_id,
                    Attachment.conversation_id.is_(None),
                )
                .order_by(Attachment.created_at)
            )
        )

    def list_selected_for_conversation(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        attachment_ids: Sequence[UUID] | None = None,
    ) -> list[Attachment]:
        """Return explicitly selected files, defaulting to current uploads.

        Workspace-scoped files are available only when their IDs are supplied;
        this prevents a generic request from implicitly reading the workspace
        library.
        """

        if attachment_ids is None:
            return self.list_current_for_conversation(workspace_id, conversation_id)
        unique_ids = tuple(dict.fromkeys(attachment_ids))
        if not unique_ids:
            return []
        selected = list(
            self.session.scalars(
                select(Attachment)
                .where(
                    Attachment.workspace_id == workspace_id,
                    Attachment.id.in_(unique_ids),
                    (Attachment.conversation_id == conversation_id)
                    | (Attachment.conversation_id.is_(None)),
                )
                .order_by(Attachment.created_at)
            )
        )
        found = {attachment.id for attachment in selected}
        missing = [str(item) for item in unique_ids if item not in found]
        if missing:
            raise AppError(
                code="attachment_selection_invalid",
                message="One or more selected attachments are not available in this workspace or conversation.",
                status_code=422,
                details={"attachment_ids": missing},
            )
        return selected

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

    def list_chunks_for_workspace(self, workspace_id: UUID) -> list[MaterialChunk]:
        return list(
            self.session.scalars(
                select(MaterialChunk)
                .join(Attachment, MaterialChunk.attachment_id == Attachment.id)
                .where(
                    MaterialChunk.workspace_id == workspace_id,
                    Attachment.workspace_id == workspace_id,
                )
                .order_by(Attachment.created_at, MaterialChunk.chunk_index)
            )
        )

    def list_chunks_for_attachments(
        self, workspace_id: UUID, conversation_id: UUID, attachment_ids: Sequence[UUID]
    ) -> list[MaterialChunk]:
        if not attachment_ids:
            return []
        return list(
            self.session.scalars(
                select(MaterialChunk)
                .join(Attachment, MaterialChunk.attachment_id == Attachment.id)
                .where(
                    MaterialChunk.workspace_id == workspace_id,
                    Attachment.workspace_id == workspace_id,
                    Attachment.id.in_(tuple(attachment_ids)),
                    (Attachment.conversation_id == conversation_id)
                    | (Attachment.conversation_id.is_(None)),
                )
                .order_by(Attachment.created_at, MaterialChunk.chunk_index)
            )
        )

    def update(self, attachment: Attachment, **values) -> Attachment:
        for key, value in values.items():
            setattr(attachment, key, value)
        self._commit()
        self.session.refresh(attachment)
        return attachment

    def add_chunks(self, chunks: list[MaterialChunk]) -> None:
        self.session.add_all(chunks)
        self._commit()

    def _commit(self) -> None:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise


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
        agent_id: str | None = None,
        attachment_ids: Sequence[UUID] | None = None,
    ) -> list[MaterialChunk]:
        conditions = [
            MaterialChunk.workspace_id == workspace_id,
            (MaterialChunk.conversation_id == conversation_id)
            | (MaterialChunk.conversation_id.is_(None)),
        ]
        if attachment_ids is not None:
            conditions.append(MaterialChunk.attachment_id.in_(tuple(attachment_ids)))
        chunks = list(self.session.scalars(select(MaterialChunk).where(*conditions)))
        if agent_id != "learning_analysis":
            chunks = [chunk for chunk in chunks if not is_learning_analysis_material(chunk)]
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
