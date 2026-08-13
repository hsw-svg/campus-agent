from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base

JsonColumn = JSON().with_variant(JSONB(), "postgresql")


class Course(Base):
    __tablename__ = "course"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("anonymous_workspace.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    teacher_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deeptutor_book_id: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("workspace_id", "template_key", name="uq_course_workspace_template_key"),
        UniqueConstraint(
            "workspace_id",
            "deeptutor_book_id",
            name="uq_course_workspace_deeptutor_book",
        ),
    )


class CourseChapter(Base):
    __tablename__ = "course_chapter"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    knowledge_points: Mapped[list] = mapped_column(JsonColumn, nullable=False, default=list)
    deeptutor_chapter_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    deeptutor_page_ids: Mapped[list] = mapped_column(JsonColumn, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("course_id", "position", name="uq_course_chapter_position"),
        UniqueConstraint(
            "course_id",
            "deeptutor_chapter_id",
            name="uq_course_chapter_deeptutor_chapter",
        ),
    )


class StudentCourseProgress(Base):
    __tablename__ = "student_course_progress"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("anonymous_workspace.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_studied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_chapter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course_chapter.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("workspace_id", "course_id", name="uq_student_course_progress_owner"),
    )


class CourseChapterProgress(Base):
    __tablename__ = "course_chapter_progress"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_progress_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("student_course_progress.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course_chapter.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("course_progress_id", "chapter_id", name="uq_course_chapter_progress"),
    )


class StudentCourseWeakPoint(Base):
    __tablename__ = "student_course_weak_point"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    course_progress_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("student_course_progress.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course_chapter.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_artifact_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("artifact.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
