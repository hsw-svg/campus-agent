from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.artifacts.repositories import ArtifactRepository
from app.integrations.storage.base import ObjectStorage
from app.services.artifact_presentations import ArtifactPresentationService
from app.workspaces.dependencies import get_session


def get_artifact_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ArtifactRepository:
    return ArtifactRepository(session)


def get_object_storage(request: Request) -> ObjectStorage:
    return request.app.state.object_storage


def get_artifact_presentation_service(request: Request) -> ArtifactPresentationService:
    return request.app.state.artifact_presentation_service
