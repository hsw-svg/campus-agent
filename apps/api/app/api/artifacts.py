from datetime import datetime
from uuid import UUID

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict

from app.artifacts.dependencies import get_artifact_repository
from app.artifacts.models import Artifact
from app.artifacts.repositories import ArtifactRepository
from app.core.errors import AppError
from app.skills.artifact_export import ArtifactExporterSkill
from app.workspaces.dependencies import get_current_workspace
from app.workspaces.models import AnonymousWorkspace

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    conversation_id: UUID
    type: str
    title: str
    content: str
    data: dict
    format: str
    created_at: datetime
    updated_at: datetime


def get_owned_artifact(
    artifacts: ArtifactRepository,
    workspace_id: UUID,
    artifact_id: UUID,
) -> Artifact:
    artifact = artifacts.get(workspace_id, artifact_id)
    if artifact is None:
        raise AppError(
            code="artifact_not_found",
            message="Artifact was not found.",
            status_code=404,
        )
    return artifact


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(
    artifact_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    artifacts: ArtifactRepository = Depends(get_artifact_repository),
) -> Artifact:
    return get_owned_artifact(artifacts, workspace.id, artifact_id)


@router.get("/{artifact_id}/export", response_class=PlainTextResponse)
def export_artifact(
    artifact_id: UUID,
    export_format: Literal["markdown", "csv"] | None = Query(default=None, alias="format"),
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    artifacts: ArtifactRepository = Depends(get_artifact_repository),
) -> PlainTextResponse:
    artifact = get_owned_artifact(artifacts, workspace.id, artifact_id)
    exporter = ArtifactExporterSkill()
    exported = (
        exporter.run_csv(artifact.data)
        if export_format == "csv"
        else exporter.run(("markdown", artifact.content))
    )
    return PlainTextResponse(
        exported.content,
        media_type=exported.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.id}.{exported.extension}"'
        },
    )
