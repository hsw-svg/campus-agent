from uuid import UUID

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.courses.models import Course, CourseChapter
from app.attachments.models import Attachment
from app.conversations.models import Conversation


class CourseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        workspace_id: UUID,
        name: str,
        description: str | None = None,
        *,
        teacher_name: str | None = None,
        starts_at: datetime | None = None,
        thumbnail_key: str | None = None,
        category: str | None = None,
    ) -> Course:
        course = Course(
            workspace_id=workspace_id,
            name=name,
            description=description,
            teacher_name=teacher_name,
            starts_at=starts_at,
            thumbnail_key=thumbnail_key,
            category=category,
        )
        self.session.add(course)
        self.session.commit()
        self.session.refresh(course)
        return course

    def list_for_workspace(self, workspace_id: UUID) -> list[Course]:
        return list(self.session.scalars(select(Course).where(Course.workspace_id == workspace_id).order_by(Course.updated_at.desc())))

    def get(self, workspace_id: UUID, course_id: UUID) -> Course | None:
        return self.session.scalar(select(Course).where(Course.id == course_id, Course.workspace_id == workspace_id))

    def get_chapter(self, course_id: UUID, chapter_id: UUID) -> CourseChapter | None:
        return self.session.scalar(
            select(CourseChapter).where(
                CourseChapter.id == chapter_id,
                CourseChapter.course_id == course_id,
            )
        )

    def update(
        self,
        course: Course,
        *,
        name: str,
        description: str | None = None,
        teacher_name: str | None = None,
        starts_at: datetime | None = None,
        thumbnail_key: str | None = None,
        category: str | None = None,
    ) -> Course:
        course.name = name
        course.description = description
        course.teacher_name = teacher_name
        course.starts_at = starts_at
        course.thumbnail_key = thumbnail_key
        course.category = category
        self.session.commit()
        self.session.refresh(course)
        return course

    def delete(self, course: Course) -> None:
        conversations = list(
            self.session.scalars(select(Conversation).where(Conversation.course_id == course.id))
        )
        attachments = list(
            self.session.scalars(select(Attachment).where(Attachment.course_id == course.id))
        )
        for attachment in attachments:
            self.session.delete(attachment)
        for conversation in conversations:
            self.session.delete(conversation)
        self.session.delete(course)
        self.session.commit()
