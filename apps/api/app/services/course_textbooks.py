from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.attachments.models import Attachment
from app.core.errors import AppError
from app.courses.models import Course, CourseChapter
from app.integrations.deeptutor.client import (
    DeepTutorClient,
    DeepTutorError,
    course_knowledge_base_name,
)
from app.services.student_courses import StudentCourseService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TutorChapterProjection:
    chapter_id: str
    title: str
    summary: str | None
    learning_objectives: list[str]
    page_ids: list[str]
    order: int


class CourseTextbookService:
    def __init__(self, session: Session, deeptutor_client: DeepTutorClient) -> None:
        self.session = session
        self.deeptutor_client = deeptutor_client
        self.student_courses = StudentCourseService(session)

    async def create_textbook(
        self,
        workspace_id: UUID,
        course_id: UUID,
        *,
        topic: str,
        use_course_materials: bool,
    ) -> dict[str, Any]:
        course = self._owned_course(workspace_id, course_id)
        if course.deeptutor_book_id:
            raise AppError(
                code="course_textbook_exists",
                message="This course already has an interactive textbook.",
                status_code=409,
            )

        knowledge_bases: list[str] = []
        if use_course_materials:
            knowledge_base_name = self._ready_course_knowledge_base(workspace_id, course_id)
            if knowledge_base_name is None:
                raise AppError(
                    code="course_materials_not_ready",
                    message="Course materials are not ready for textbook generation.",
                    status_code=409,
                )
            knowledge_bases.append(knowledge_base_name)

        intent = _textbook_intent(course, topic)
        try:
            result = await self.deeptutor_client.create_or_compile_book(
                {
                    "user_intent": intent,
                    "language": "zh",
                    "knowledge_bases": knowledge_bases,
                }
            )
        except DeepTutorError as error:
            raise AppError(
                code=error.code,
                message=error.message,
                status_code=error.status_code,
                details=error.details,
            ) from error

        book_id, tutor_chapters = parse_created_textbook(result)
        try:
            self._bind_textbook(course, book_id, tutor_chapters)
            self.session.commit()
        except SQLAlchemyError as error:
            self.session.rollback()
            logger.exception(
                "Failed to persist course textbook binding",
                extra={"course_id": str(course_id), "deeptutor_book_id": book_id},
            )
            raise AppError(
                code="course_textbook_binding_failed",
                message="The interactive textbook was created but could not be bound to the course.",
                status_code=500,
                details={"deeptutor_book_id": book_id},
            ) from error
        return self.student_courses.get_detail(workspace_id, course_id)

    def _owned_course(self, workspace_id: UUID, course_id: UUID) -> Course:
        course = self.session.scalar(
            select(Course).where(Course.id == course_id, Course.workspace_id == workspace_id)
        )
        if course is None:
            raise AppError(code="course_not_found", message="Course was not found.", status_code=404)
        return course

    def _ready_course_knowledge_base(self, workspace_id: UUID, course_id: UUID) -> str | None:
        expected_name = course_knowledge_base_name(str(course_id))
        attachment = self.session.scalar(
            select(Attachment)
            .where(
                Attachment.workspace_id == workspace_id,
                Attachment.course_id == course_id,
                Attachment.scope == "workspace",
                Attachment.status != "failed",
                Attachment.knowledge_base_name == expected_name,
                Attachment.knowledge_base_status.in_(("queued", "syncing", "ready")),
            )
            .order_by(Attachment.created_at.desc())
        )
        return expected_name if attachment is not None else None

    def _bind_textbook(
        self,
        course: Course,
        book_id: str,
        tutor_chapters: list[TutorChapterProjection],
    ) -> None:
        existing = list(
            self.session.scalars(
                select(CourseChapter)
                .where(CourseChapter.course_id == course.id)
                .order_by(CourseChapter.position.asc())
            )
        )
        if existing:
            for chapter, tutor_chapter in zip(existing, tutor_chapters, strict=False):
                chapter.deeptutor_chapter_id = tutor_chapter.chapter_id
                chapter.deeptutor_page_ids = tutor_chapter.page_ids
        else:
            for position, tutor_chapter in enumerate(tutor_chapters, start=1):
                self.session.add(
                    CourseChapter(
                        course_id=course.id,
                        title=tutor_chapter.title,
                        summary=tutor_chapter.summary,
                        position=position,
                        estimated_minutes=45,
                        knowledge_points=tutor_chapter.learning_objectives,
                        deeptutor_chapter_id=tutor_chapter.chapter_id,
                        deeptutor_page_ids=tutor_chapter.page_ids,
                    )
                )
        course.deeptutor_book_id = book_id
        self.session.flush()


def parse_created_textbook(value: Any) -> tuple[str, list[TutorChapterProjection]]:
    if not isinstance(value, Mapping):
        raise _invalid_textbook_response()
    book = value.get("book")
    spine = value.get("spine")
    if not isinstance(book, Mapping) or not isinstance(spine, Mapping):
        raise _invalid_textbook_response()
    book_id = book.get("id")
    raw_chapters = spine.get("chapters")
    if not isinstance(book_id, str) or not book_id.strip() or not isinstance(raw_chapters, list):
        raise _invalid_textbook_response()

    chapters: list[TutorChapterProjection] = []
    for index, raw in enumerate(raw_chapters):
        if not isinstance(raw, Mapping) or raw.get("auto_overview") is True:
            continue
        chapter_id = raw.get("id")
        title = raw.get("title")
        if not isinstance(chapter_id, str) or not chapter_id.strip():
            raise _invalid_textbook_response()
        if not isinstance(title, str) or not title.strip():
            raise _invalid_textbook_response()
        raw_page_ids = raw.get("page_ids")
        objectives = raw.get("learning_objectives")
        summary = raw.get("summary")
        order = raw.get("order")
        page_ids = [
            item.strip()
            for item in raw_page_ids
            if isinstance(item, str) and item.strip()
        ] if isinstance(raw_page_ids, list) else []
        if not page_ids:
            raise _invalid_textbook_response()
        chapters.append(
            TutorChapterProjection(
                chapter_id=chapter_id.strip(),
                title=title.strip(),
                summary=summary.strip() if isinstance(summary, str) and summary.strip() else None,
                learning_objectives=[
                    item.strip()
                    for item in objectives
                    if isinstance(item, str) and item.strip()
                ] if isinstance(objectives, list) else [],
                page_ids=page_ids,
                order=order if isinstance(order, int) else index,
            )
        )
    if not chapters:
        raise _invalid_textbook_response()
    chapters.sort(key=lambda item: item.order)
    return book_id.strip(), chapters


def _textbook_intent(course: Course, topic: str) -> str:
    description = f"\n课程说明：{course.description.strip()}" if course.description and course.description.strip() else ""
    return f"为课程《{course.name}》创建中文交互教材。\n学习主题：{topic.strip()}{description}"


def _invalid_textbook_response() -> AppError:
    return AppError(
        code="deeptutor_invalid_response",
        message="DeepTutor returned an invalid textbook structure.",
        status_code=502,
    )
