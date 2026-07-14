from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.workspaces.models import AnonymousWorkspace


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, role: str, token_hash: str) -> AnonymousWorkspace:
        workspace = AnonymousWorkspace(role=role, token_hash=token_hash)
        self.session.add(workspace)
        self.session.commit()
        self.session.refresh(workspace)
        return workspace

    def get_by_token_hash(self, token_hash: str) -> AnonymousWorkspace | None:
        return self.session.scalar(
            select(AnonymousWorkspace).where(AnonymousWorkspace.token_hash == token_hash)
        )

    def delete(self, workspace: AnonymousWorkspace) -> None:
        self.session.delete(workspace)
        self.session.commit()

    def touch(self, workspace: AnonymousWorkspace) -> AnonymousWorkspace:
        workspace.last_active_at = datetime.now(timezone.utc)
        self.session.commit()
        self.session.refresh(workspace)
        return workspace
