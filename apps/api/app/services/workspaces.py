import hashlib
import secrets

from app.repositories.workspaces import WorkspaceRepository
from app.workspaces.models import AnonymousWorkspace


def create_workspace(repository: WorkspaceRepository, role: str) -> tuple[AnonymousWorkspace, str]:
    """Create a workspace and return its only copy of an opaque credential."""

    token = secrets.token_urlsafe(32)
    workspace = repository.create(role=role, token_hash=hash_workspace_token(token))
    return workspace, token


def hash_workspace_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
