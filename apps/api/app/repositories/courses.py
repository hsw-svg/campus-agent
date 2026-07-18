from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.courses.models import Course


class CourseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, workspace_id: UUID, name: str, description: str | None = None) -> Course:
        course = Course(workspace_id=workspace_id, name=name, description=description)
        self.session.add(course)
        self.session.commit()
        self.session.refresh(course)
        return course

    def list_for_workspace(self, workspace_id: UUID) -> list[Course]:
        return list(self.session.scalars(select(Course).where(Course.workspace_id == workspace_id).order_by(Course.updated_at.desc())))

    def get(self, workspace_id: UUID, course_id: UUID) -> Course | None:
        return self.session.scalar(select(Course).where(Course.id == course_id, Course.workspace_id == workspace_id))
