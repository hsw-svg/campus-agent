from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.artifacts.models import Artifact
from app.core.errors import AppError


class ArtifactRepository:
    """Artifact access that always includes the caller's workspace."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values) -> Artifact:
        artifact = Artifact(**values)
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def get(self, workspace_id: UUID, artifact_id: UUID) -> Artifact | None:
        return self.session.scalar(
            select(Artifact).where(
                Artifact.id == artifact_id,
                Artifact.workspace_id == workspace_id,
            )
        )

    def list_for_conversation(self, workspace_id: UUID, conversation_id: UUID) -> list[Artifact]:
        return list(
            self.session.scalars(
                select(Artifact)
                .where(
                    Artifact.workspace_id == workspace_id,
                    Artifact.conversation_id == conversation_id,
                )
                .order_by(Artifact.created_at)
            )
        )

    def list_selected_for_conversation(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        artifact_ids: tuple[UUID, ...],
    ) -> list[Artifact]:
        if not artifact_ids:
            return []
        unique_ids = tuple(dict.fromkeys(artifact_ids))
        selected = list(
            self.session.scalars(
                select(Artifact)
                .where(
                    Artifact.workspace_id == workspace_id,
                    Artifact.conversation_id == conversation_id,
                    Artifact.id.in_(unique_ids),
                )
                .order_by(Artifact.created_at)
            )
        )
        found = {artifact.id for artifact in selected}
        missing = [str(item) for item in unique_ids if item not in found]
        if missing:
            raise AppError(
                code="artifact_selection_invalid",
                message="One or more selected artifacts are not available in this conversation.",
                status_code=422,
                details={"artifact_ids": missing},
            )
        return selected
