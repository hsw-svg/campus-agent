from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.artifacts.repositories import ArtifactRepository
from app.workspaces.dependencies import get_session


def get_artifact_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ArtifactRepository:
    return ArtifactRepository(session)
