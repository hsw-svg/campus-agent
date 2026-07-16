from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.artifacts.models import Artifact


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
