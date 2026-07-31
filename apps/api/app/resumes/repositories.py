from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.resumes.models import StudentResumeProfile


class StudentResumeProfileRepository:
    """Current-resume access constrained to the owning workspace."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, workspace_id: UUID) -> StudentResumeProfile | None:
        return self.session.scalar(
            select(StudentResumeProfile).where(
                StudentResumeProfile.workspace_id == workspace_id
            )
        )

    def set_current(
        self, workspace_id: UUID, attachment_id: UUID
    ) -> StudentResumeProfile:
        profile = self.get(workspace_id)
        if profile is None:
            profile = StudentResumeProfile(
                workspace_id=workspace_id,
                current_attachment_id=attachment_id,
            )
            self.session.add(profile)
        else:
            profile.current_attachment_id = attachment_id
        self.session.commit()
        self.session.refresh(profile)
        return profile
