from typing import Any, NotRequired, TypedDict, Unpack
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.artifacts.models import Artifact
from app.core.errors import AppError


class ArtifactValues(TypedDict):
    workspace_id: NotRequired[UUID]
    conversation_id: NotRequired[UUID]
    type: NotRequired[str]
    title: NotRequired[str]
    content: NotRequired[str]
    data: NotRequired[dict[str, Any]]
    format: NotRequired[str]
    id: NotRequired[UUID]
    object_key: NotRequired[str | None]
    mime_type: NotRequired[str | None]
    sha256: NotRequired[str | None]
    size_bytes: NotRequired[int | None]
    page_count: NotRequired[int | None]
    preview_status: NotRequired[str | None]
    preview_manifest: NotRequired[list[dict[str, Any]] | None]


class ArtifactRepository:
    """Artifact access that always includes the caller's workspace."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values: Unpack[ArtifactValues]) -> Artifact:
        artifact = Artifact(**values)
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def update(self, artifact: Artifact, **values: Unpack[ArtifactValues]) -> Artifact:
        for key, value in values.items():
            setattr(artifact, key, value)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def delete(self, artifact: Artifact) -> None:
        self.session.delete(artifact)
        self.session.commit()

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

    def latest_by_conversation(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        artifact_type: str,
    ) -> Artifact | None:
        return self.session.scalar(
            select(Artifact)
            .where(
                Artifact.workspace_id == workspace_id,
                Artifact.conversation_id == conversation_id,
                Artifact.type == artifact_type,
            )
            .order_by(Artifact.created_at.desc())
            .limit(1)
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
