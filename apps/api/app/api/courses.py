from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.agents.repositories import AgentHistoryRecord, AgentRunRepository
from app.agents.dependencies import get_agent_run_repository
from app.core.errors import AppError
from app.repositories.courses import CourseRepository
from app.services.student_courses import StudentCourseService
from app.services.course_textbooks import CourseTextbookService
from app.workspaces.dependencies import get_current_workspace, get_session
from app.workspaces.models import AnonymousWorkspace
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/courses", tags=["courses"])


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    teacher_name: str | None
    starts_at: datetime | None
    thumbnail_key: str | None
    category: str | None
    deeptutor_book_id: str | None
    created_at: datetime
    updated_at: datetime


class CreateCourseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    teacher_name: str | None = Field(default=None, max_length=120)
    starts_at: datetime | None = None
    thumbnail_key: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, max_length=64)


class UpdateCourseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    teacher_name: str | None = Field(default=None, max_length=120)
    starts_at: datetime | None = None
    thumbnail_key: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, max_length=64)


class CourseSummaryResponse(CourseResponse):
    chapter_count: int
    completed_chapter_count: int
    progress_percent: int
    started: bool
    last_studied_at: datetime | None


class CourseChapterResponse(BaseModel):
    id: UUID
    title: str
    summary: str | None
    position: int
    estimated_minutes: int | None
    knowledge_points: list[str]
    deeptutor_chapter_id: str | None
    deeptutor_page_ids: list[str]
    completed: bool
    current: bool


class CourseWeakPointResponse(BaseModel):
    id: UUID
    chapter_id: UUID | None
    name: str
    recommendation: str


class CourseDetailResponse(CourseSummaryResponse):
    chapters: list[CourseChapterResponse]
    current_chapter_id: UUID | None
    weak_points: list[CourseWeakPointResponse]


class CreateCourseTextbookRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    use_course_materials: bool = False


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


def get_student_course_service(session: Session = Depends(get_session)) -> StudentCourseService:
    return StudentCourseService(session)


@router.get("", response_model=list[CourseSummaryResponse])
def list_courses(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    student_courses: StudentCourseService = Depends(get_student_course_service),
) -> list:
    return student_courses.list_summaries(workspace.id)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CreateCourseRequest, workspace: AnonymousWorkspace = Depends(get_current_workspace), courses: CourseRepository = Depends(get_course_repository)) -> object:
    return courses.create(
        workspace.id,
        payload.name.strip(),
        payload.description,
        teacher_name=payload.teacher_name,
        starts_at=payload.starts_at,
        thumbnail_key=payload.thumbnail_key,
        category=payload.category,
    )


@router.post("/defaults", response_model=list[CourseSummaryResponse])
def initialize_default_courses(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    student_courses: StudentCourseService = Depends(get_student_course_service),
) -> list:
    require_student_workspace(workspace)
    return student_courses.ensure_defaults(workspace.id)


@router.get("/{course_id}", response_model=CourseDetailResponse)
def get_course_detail(
    course_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    student_courses: StudentCourseService = Depends(get_student_course_service),
) -> dict:
    return student_courses.get_detail(workspace.id, course_id)


@router.post("/{course_id}/start", response_model=CourseDetailResponse)
def start_course(
    course_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    student_courses: StudentCourseService = Depends(get_student_course_service),
) -> dict:
    require_student_workspace(workspace)
    return student_courses.start_course(workspace.id, course_id)


@router.post("/{course_id}/textbook", response_model=CourseDetailResponse)
async def create_course_textbook(
    course_id: UUID,
    payload: CreateCourseTextbookRequest,
    request: Request,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    session: Session = Depends(get_session),
) -> dict:
    require_student_workspace(workspace)
    service = CourseTextbookService(session, request.app.state.deeptutor_client)
    return await service.create_textbook(
        workspace.id,
        course_id,
        topic=payload.topic.strip(),
        use_course_materials=payload.use_course_materials,
    )


@router.post("/{course_id}/chapters/{chapter_id}/start", response_model=CourseDetailResponse)
def start_course_chapter(
    course_id: UUID,
    chapter_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    student_courses: StudentCourseService = Depends(get_student_course_service),
) -> dict:
    require_student_workspace(workspace)
    return student_courses.start_chapter(workspace.id, course_id, chapter_id)


@router.post("/{course_id}/chapters/{chapter_id}/complete", response_model=CourseDetailResponse)
def complete_course_chapter(
    course_id: UUID,
    chapter_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    student_courses: StudentCourseService = Depends(get_student_course_service),
) -> dict:
    require_student_workspace(workspace)
    return student_courses.complete_chapter(workspace.id, course_id, chapter_id)


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: UUID,
    payload: UpdateCourseRequest,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    courses: CourseRepository = Depends(get_course_repository),
) -> object:
    course = get_owned_course(courses, workspace.id, course_id)
    return courses.update(
        course,
        name=payload.name.strip(),
        description=payload.description,
        teacher_name=payload.teacher_name if payload.teacher_name is not None else course.teacher_name,
        starts_at=payload.starts_at if payload.starts_at is not None else course.starts_at,
        thumbnail_key=payload.thumbnail_key if payload.thumbnail_key is not None else course.thumbnail_key,
        category=payload.category if payload.category is not None else course.category,
    )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    courses: CourseRepository = Depends(get_course_repository),
) -> None:
    course = get_owned_course(courses, workspace.id, course_id)
    courses.delete(course)


@router.get("/{course_id}/agent-history", response_model=list[AgentHistoryResponse])
def list_course_agent_history(
    course_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    courses: CourseRepository = Depends(get_course_repository),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
) -> list[AgentHistoryResponse]:
    get_owned_course(courses, workspace.id, course_id)
    return [_history_response(record) for record in agent_runs.list_for_course(workspace.id, course_id)]


@router.delete("/{course_id}/agent-history/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course_agent_history(
    course_id: UUID,
    run_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    courses: CourseRepository = Depends(get_course_repository),
    agent_runs: AgentRunRepository = Depends(get_agent_run_repository),
) -> None:
    get_owned_course(courses, workspace.id, course_id)
    run = agent_runs.get(workspace.id, run_id)
    if run is None:
        raise AppError(code="agent_run_not_found", message="Agent run was not found.", status_code=404)
    agent_runs.delete(run)


def get_owned_course(courses: CourseRepository, workspace_id: UUID, course_id: UUID):
    course = courses.get(workspace_id, course_id)
    if course is None:
        raise AppError(code="course_not_found", message="Course was not found.", status_code=404)
    return course


def require_student_workspace(workspace: AnonymousWorkspace) -> None:
    if workspace.role != "student":
        raise AppError(
            code="student_course_center_forbidden",
            message="Student course progress is only available to student workspaces.",
            status_code=403,
        )


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
