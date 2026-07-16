from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.models import AgentRun


class AgentRunRepository:
    """Agent run access that always includes the caller's workspace."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **values) -> AgentRun:
        run = AgentRun(**values)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get(self, workspace_id: UUID, run_id: UUID) -> AgentRun | None:
        return self.session.scalar(
            select(AgentRun).where(
                AgentRun.id == run_id,
                AgentRun.workspace_id == workspace_id,
            )
        )

    def update(self, run: AgentRun, **values) -> AgentRun:
        for key, value in values.items():
            setattr(run, key, value)
        self.session.commit()
        self.session.refresh(run)
        return run
