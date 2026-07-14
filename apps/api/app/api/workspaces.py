from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict

from app.core.errors import AppError
from app.repositories.workspaces import WorkspaceRepository
from app.services.workspaces import create_workspace
from app.workspaces.dependencies import get_current_workspace, get_workspace_repository
from app.workspaces.models import AnonymousWorkspace


router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class WorkspaceRole(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class CreateWorkspaceRequest(BaseModel):
    role: WorkspaceRole


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: WorkspaceRole


class CreateWorkspaceResponse(BaseModel):
    workspace: WorkspaceResponse
    token: str


@router.post("", response_model=CreateWorkspaceResponse, status_code=status.HTTP_201_CREATED)
def post_workspace(
    payload: CreateWorkspaceRequest,
    repository: WorkspaceRepository = Depends(get_workspace_repository),
) -> CreateWorkspaceResponse:
    workspace, token = create_workspace(repository, payload.role.value)
    return CreateWorkspaceResponse(workspace=workspace, token=token)


@router.get("/current", response_model=WorkspaceResponse)
def get_current_workspace_response(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
) -> AnonymousWorkspace:
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace_by_id(
    workspace_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
) -> AnonymousWorkspace:
    if workspace.id != workspace_id:
        raise AppError(
            code="workspace_not_found",
            message="Workspace was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return workspace


@router.delete("/current", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_workspace(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    repository: WorkspaceRepository = Depends(get_workspace_repository),
) -> None:
    repository.delete(workspace)
