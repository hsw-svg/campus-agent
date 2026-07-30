from datetime import datetime
import hashlib
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, ConfigDict

from app.artifacts.dependencies import get_artifact_repository, get_object_storage
from app.artifacts.models import Artifact
from app.artifacts.repositories import ArtifactRepository
from app.core.errors import AppError
from app.integrations.storage.base import ObjectStorage
from app.skills.artifact_export import ArtifactExporterSkill
from app.skills.slide_deck_pptx import SlideDeckPptxSkill
from app.workspaces.dependencies import get_current_workspace
from app.workspaces.models import AnonymousWorkspace

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


class PresentationDescriptor(BaseModel):
    status: str | None
    mime_type: str | None
    sha256: str | None
    size_bytes: int | None
    page_count: int | None
    download_url: str


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
    object_key: str | None
    mime_type: str | None
    sha256: str | None
    size_bytes: int | None
    page_count: int | None
    preview_status: str | None
    presentation: PresentationDescriptor | None
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


@router.get("/{artifact_id}/export")
def export_artifact(
    artifact_id: UUID,
    export_format: Literal["markdown", "csv", "pptx"] | None = Query(default=None, alias="format"),
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    artifacts: ArtifactRepository = Depends(get_artifact_repository),
    storage: ObjectStorage = Depends(get_object_storage),
) -> Response:
    artifact = get_owned_artifact(artifacts, workspace.id, artifact_id)
    if export_format == "pptx":
        if artifact.type != "slide_deck":
            raise AppError(
                code="artifact_export_format_invalid",
                message="pptx 导出仅支持 slide_deck 类型的成果。",
                status_code=400,
                details={"artifact_type": artifact.type},
            )
        if artifact.object_key is not None:
            _validate_authoritative_presentation(artifact)
            content = _read_authoritative_object(storage, artifact.object_key, "artifact_presentation_unavailable")
            if len(content) != artifact.size_bytes or hashlib.sha256(content).hexdigest() != artifact.sha256:
                raise AppError(
                    code="artifact_presentation_corrupt",
                    message="The stored authoritative presentation failed integrity validation.",
                    status_code=409,
                )
            return Response(
                content=content,
                media_type=artifact.mime_type,
                headers={"Content-Disposition": f'attachment; filename="{artifact.id}.pptx"'},
            )
        exported = SlideDeckPptxSkill().run(artifact.data)
        return Response(
            content=exported.content,
            media_type=exported.media_type,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{artifact.id}.{exported.extension}"'
                )
            },
        )
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


def _validate_authoritative_presentation(artifact: Artifact) -> None:
    expected_mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    if (
        artifact.mime_type != expected_mime
        or not artifact.sha256
        or artifact.size_bytes is None
        or artifact.size_bytes < 1
        or artifact.page_count is None
        or artifact.page_count < 1
    ):
        raise AppError(
            code="artifact_presentation_invalid",
            message="The authoritative presentation metadata is incomplete.",
            status_code=409,
        )


def _read_authoritative_object(storage: ObjectStorage, key: str, code: str) -> bytes:
    try:
        return storage.get(key)
    except Exception as error:
        raise AppError(
            code=code,
            message="The authoritative stored object is unavailable.",
            status_code=409,
        ) from error
