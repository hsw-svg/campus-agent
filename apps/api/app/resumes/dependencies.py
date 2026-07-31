from fastapi import Depends
from sqlalchemy.orm import Session

from app.resumes.repositories import StudentResumeProfileRepository
from app.workspaces.dependencies import get_session


def get_student_resume_profile_repository(
    session: Session = Depends(get_session),
) -> StudentResumeProfileRepository:
    return StudentResumeProfileRepository(session)
