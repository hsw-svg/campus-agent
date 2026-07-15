from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.registry import AUTO_AGENT_ID, list_agents
from app.workspaces.dependencies import get_current_workspace
from app.workspaces.models import AnonymousWorkspace

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str


class AgentListResponse(BaseModel):
    role: str
    auto_agent_id: str
    agents: list[AgentResponse]


@router.get("", response_model=AgentListResponse)
def get_agents(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
) -> AgentListResponse:
    """Return only the agents whitelisted for the caller's role."""

    agents = [
        AgentResponse(id=agent.id, name=agent.name, description=agent.description)
        for agent in list_agents(workspace.role)
    ]
    return AgentListResponse(
        role=workspace.role,
        auto_agent_id=AUTO_AGENT_ID,
        agents=agents,
    )
