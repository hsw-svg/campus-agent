from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.attachments.repositories import AttachmentRepository
from app.workspaces.dependencies import get_session


def get_attachment_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AttachmentRepository:
    return AttachmentRepository(session)


def get_object_storage(request: Request):
    return request.app.state.object_storage
