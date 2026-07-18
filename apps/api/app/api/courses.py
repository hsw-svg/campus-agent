from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from app.agents.repositories import AgentHistoryRecord, AgentRunRepository
from app.agents.dependencies import get_agent_run_repository
from app.core.errors import AppError
from app.repositories.courses import CourseRepository
from app.workspaces.dependencies import get_current_workspace, get_session
from app.workspaces.models import AnonymousWorkspace
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/courses", tags=["courses"])


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class CreateCourseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)


class CourseArtifactResponse(BaseModel):
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


class AgentHistoryResponse(BaseModel):
    run_id: UUID
    conversation_id: UUID
    conversation_title: str
    agent_id: str | None
    status: str
    summary: str | None
    artifact: CourseArtifactResponse | None
    created_at: datetime
    updated_at: datetime


def get_course_repository(session: Session = Depends(get_session)) -> CourseRepository:
    return CourseRepository(session)


@router.get("", response_model=list[CourseResponse])
def list_courses(workspace: AnonymousWorkspace = Depends(get_current_workspace), courses: CourseRepository = Depends(get_course_repository)) -> list:
    return courses.list_for_workspace(workspace.id)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CreateCourseRequest, workspace: AnonymousWorkspace = Depends(get_current_workspace), courses: CourseRepository = Depends(get_course_repository)) -> object:
    return courses.create(workspace.id, payload.name.strip(), payload.description)


@router.get("/{course_id}/agent-history", response_model=list[AgentHistoryResponse])
def list_course_agent_history(
    course_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    courses: CourseRepository = Depends(get_course_repository),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
) -> list[AgentHistoryResponse]:
    get_owned_course(courses, workspace.id, course_id)
    return [_history_response(record) for record in agent_runs.list_for_course(workspace.id, course_id)]


def get_owned_course(courses: CourseRepository, workspace_id: UUID, course_id: UUID):
    course = courses.get(workspace_id, course_id)
    if course is None:
        raise AppError(code="course_not_found", message="Course was not found.", status_code=404)
    return course


def _history_response(record: AgentHistoryRecord) -> AgentHistoryResponse:
    artifact = record.artifact
    summary = record.result_message.content.strip() if record.result_message else None
    if summary and len(summary) > 240:
        summary = f"{summary[:237]}..."
    return AgentHistoryResponse(
        run_id=record.run.id,
        conversation_id=record.conversation.id,
        conversation_title=record.conversation.title,
        agent_id=record.run.agent_id,
        status=record.run.status,
        summary=summary or None,
        artifact=CourseArtifactResponse.model_validate(artifact) if artifact else None,
        created_at=record.run.created_at,
        updated_at=record.run.updated_at,
    )
