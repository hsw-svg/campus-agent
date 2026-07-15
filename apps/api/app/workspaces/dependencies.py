from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories.workspaces import WorkspaceRepository
from app.services.workspaces import hash_workspace_token
from app.workspaces.models import AnonymousWorkspace


def get_session(request: Request) -> Generator[Session, None, None]:
    with request.app.state.session_factory() as session:
        yield session


def get_chat_provider(request: Request):
    return request.app.state.chat_provider


def get_workspace_repository(
    session: Annotated[Session, Depends(get_session)],
) -> WorkspaceRepository:
    return WorkspaceRepository(session)


def get_current_workspace(
    token: Annotated[str | None, Header(alias="X-Workspace-Token")] = None,
    repository: WorkspaceRepository = Depends(get_workspace_repository),
) -> AnonymousWorkspace:
    if not token:
        raise AppError(
            code="workspace_credentials_required",
            message="Workspace credentials are required.",
            status_code=401,
        )

    workspace = repository.get_by_token_hash(hash_workspace_token(token))
    if workspace is None:
        raise AppError(
            code="workspace_not_found",
            message="Workspace credentials are invalid or expired.",
            status_code=401,
        )
    return repository.touch(workspace)
