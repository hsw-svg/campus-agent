from __future__ import annotations

import json
from pathlib import PurePath
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.repositories import AgentHistoryRecord, AgentRunRepository
from app.attachments.models import Attachment
from app.attachments.repositories import AttachmentRepository
from app.core.errors import AppError
from app.repositories.conversations import ConversationRepository
from app.resumes.repositories import StudentResumeProfileRepository
from app.services.student_courses import StudentCourseService


RESUME_AGENT_ID = "resume_helper"
RESUME_ARTIFACT_TYPE = "resume_analysis"
RESUME_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_SELECTED_COURSES = 24


class ResumeAssistantService:
    def __init__(
        self,
        session: Session,
        profiles: StudentResumeProfileRepository,
        attachments: AttachmentRepository,
        conversations: ConversationRepository,
        agent_runs: AgentRunRepository,
    ) -> None:
        self.session = session
        self.profiles = profiles
        self.attachments = attachments
        self.conversations = conversations
        self.agent_runs = agent_runs
        self.student_courses = StudentCourseService(session)

    def get_current_attachment(self, workspace_id: UUID) -> Attachment | None:
        profile = self.profiles.get(workspace_id)
        if profile is None or profile.current_attachment_id is None:
            return None
        return self.attachments.get(workspace_id, profile.current_attachment_id)

    def set_current_attachment(
        self, workspace_id: UUID, attachment_id: UUID
    ) -> Attachment:
        attachment = self._validated_resume_attachment(workspace_id, attachment_id)
        self.profiles.set_current(workspace_id, attachment.id)
        return attachment

    def prepare_analysis(
        self,
        *,
        workspace_id: UUID,
        attachment_id: UUID,
        target_role: str | None,
        job_description: str | None,
        selected_course_ids: list[UUID],
    ) -> tuple[Any, str, tuple[str, ...]]:
        attachment = self._validated_resume_attachment(workspace_id, attachment_id)
        current = self.get_current_attachment(workspace_id)
        if current is None or current.id != attachment.id:
            raise AppError(
                code="resume_attachment_not_current",
                message="The selected resume is no longer the current resume.",
                status_code=409,
            )
        unique_course_ids = list(dict.fromkeys(selected_course_ids))
        if len(unique_course_ids) > MAX_SELECTED_COURSES:
            raise AppError(
                code="resume_course_selection_too_large",
                message=f"Select at most {MAX_SELECTED_COURSES} courses.",
                status_code=422,
            )
        course_snapshots = [
            self._course_snapshot(workspace_id, course_id)
            for course_id in unique_course_ids
        ]
        normalized_target = _optional_text(target_role)
        normalized_job_description = _optional_text(job_description)
        analysis_input = {
            "resume_attachment_id": str(attachment.id),
            "resume_filename": attachment.filename,
            "target_role": normalized_target,
            "job_description": normalized_job_description,
            "selected_courses": course_snapshots,
        }
        title_target = normalized_target or "通用优化"
        conversation = self.conversations.create(
            workspace_id=workspace_id,
            title=f"简历分析 · {title_target}"[:200],
            agent_id=RESUME_AGENT_ID,
        )
        content = json.dumps(analysis_input, ensure_ascii=False)
        input_refs = (
            f"attachment:{attachment.id}",
            *(f"course:{course_id}" for course_id in unique_course_ids),
        )
        return conversation, content, input_refs

    def list_history(self, workspace_id: UUID) -> list[AgentHistoryRecord]:
        return self.agent_runs.list_for_agent(workspace_id, RESUME_AGENT_ID)

    def delete_history(self, workspace_id: UUID, run_id: UUID) -> None:
        run = self.agent_runs.get(workspace_id, run_id)
        if run is None or run.agent_id != RESUME_AGENT_ID:
            raise AppError(
                code="resume_analysis_not_found",
                message="Resume analysis was not found.",
                status_code=404,
            )
        if run.status in {"running", "routed", "awaiting_confirmation"}:
            raise AppError(
                code="resume_analysis_running",
                message="A running resume analysis cannot be deleted.",
                status_code=409,
            )
        conversation = self.conversations.get(workspace_id, run.conversation_id)
        if conversation is None:
            raise AppError(
                code="resume_analysis_not_found",
                message="Resume analysis was not found.",
                status_code=404,
            )
        self.conversations.delete(conversation)

    def attachment_for_record(
        self, workspace_id: UUID, record: AgentHistoryRecord
    ) -> Attachment | None:
        selected = record.run.selected_attachment_ids or []
        if not selected:
            return None
        try:
            attachment_id = UUID(str(selected[0]))
        except (TypeError, ValueError):
            return None
        return self.attachments.get(workspace_id, attachment_id)

    def _validated_resume_attachment(
        self, workspace_id: UUID, attachment_id: UUID
    ) -> Attachment:
        attachment = self.attachments.get(workspace_id, attachment_id)
        if attachment is None:
            raise AppError(
                code="resume_attachment_not_found",
                message="Resume attachment was not found.",
                status_code=404,
            )
        if (
            attachment.scope != "workspace"
            or attachment.conversation_id is not None
            or attachment.course_id is not None
        ):
            raise AppError(
                code="resume_attachment_invalid_scope",
                message="The resume must be a general workspace attachment.",
                status_code=422,
            )
        if PurePath(attachment.filename).suffix.lower() not in RESUME_EXTENSIONS:
            raise AppError(
                code="resume_attachment_type_invalid",
                message="Resume files must be PDF, DOCX, TXT, or Markdown.",
                status_code=422,
            )
        if (
            attachment.status not in {"indexed", "degraded"}
            or attachment.extracted_chars <= 0
        ):
            raise AppError(
                code="resume_attachment_text_unavailable",
                message=attachment.status_message
                or "The resume does not contain readable text.",
                status_code=422,
            )
        return attachment

    def _course_snapshot(self, workspace_id: UUID, course_id: UUID) -> dict[str, Any]:
        detail = self.student_courses.get_detail(workspace_id, course_id)
        if not detail["started"]:
            raise AppError(
                code="resume_course_not_started",
                message="Only started courses can be used as resume evidence.",
                status_code=422,
                details={"course_id": str(course_id)},
            )
        completed_chapters = [
            {
                "title": chapter["title"],
                "knowledge_points": chapter["knowledge_points"],
            }
            for chapter in detail["chapters"]
            if chapter["completed"]
        ]
        current_chapter = next(
            (chapter["title"] for chapter in detail["chapters"] if chapter["current"]),
            None,
        )
        return {
            "course_id": str(detail["id"]),
            "name": detail["name"],
            "category": detail["category"],
            "progress_percent": detail["progress_percent"],
            "completed_chapters": completed_chapters,
            "current_chapter": current_chapter,
            "weak_points": [
                {
                    "name": item["name"],
                    "recommendation": item["recommendation"],
                }
                for item in detail["weak_points"]
            ],
        }


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
