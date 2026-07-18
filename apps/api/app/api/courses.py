from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

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


def get_course_repository(session: Session = Depends(get_session)) -> CourseRepository:
    return CourseRepository(session)


@router.get("", response_model=list[CourseResponse])
def list_courses(workspace: AnonymousWorkspace = Depends(get_current_workspace), courses: CourseRepository = Depends(get_course_repository)) -> list:
    return courses.list_for_workspace(workspace.id)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CreateCourseRequest, workspace: AnonymousWorkspace = Depends(get_current_workspace), courses: CourseRepository = Depends(get_course_repository)) -> object:
    return courses.create(workspace.id, payload.name.strip(), payload.description)


def get_owned_course(courses: CourseRepository, workspace_id: UUID, course_id: UUID):
    course = courses.get(workspace_id, course_id)
    if course is None:
        raise AppError(code="course_not_found", message="Course was not found.", status_code=404)
    return course
