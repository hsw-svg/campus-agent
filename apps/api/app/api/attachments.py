from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel, ConfigDict

from app.attachments.dependencies import get_attachment_repository, get_object_storage
from app.attachments.parsing import validate_filename
from app.attachments.repositories import AttachmentRepository
from app.core.errors import AppError
from app.integrations.embedding.providers import EmbeddingProvider
from app.integrations.storage.base import ObjectStorage
from app.services.attachments import process_attachment
from app.services.conversations import get_owned_conversation
from app.repositories.conversations import ConversationRepository
from app.conversations.dependencies import get_conversation_repository
from app.workspaces.dependencies import (
    get_current_workspace,
    get_embedding_provider,
)
from app.workspaces.models import AnonymousWorkspace

router = APIRouter(prefix="/api/conversations", tags=["attachments"])
workspace_attachment_router = APIRouter(prefix="/api/workspaces", tags=["attachments"])


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID | None
    filename: str
    content_type: str
    size_bytes: int
    scope: str
    status: str
    status_message: str | None
    extracted_chars: int
    created_at: datetime
    updated_at: datetime


@router.post(
    "/{conversation_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    conversation_id: UUID,
    file: UploadFile = File(...),
    scope: str = Form("conversation"),
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
    storage: ObjectStorage = Depends(get_object_storage),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> AttachmentResponse:
    conversation = get_owned_conversation(conversations, workspace.id, conversation_id)
    if scope not in {"conversation", "workspace"}:
        raise AppError(
            code="invalid_attachment_scope",
            message="Attachment scope must be conversation or workspace.",
            status_code=400,
        )
    return await _create_uploaded_attachment(
        file=file,
        workspace=workspace,
        conversation_id=conversation.id if scope == "conversation" else None,
        scope=scope,
        attachments=attachments,
        storage=storage,
        embedding_provider=embedding_provider,
    )


@router.get("/{conversation_id}/attachments", response_model=list[AttachmentResponse])
def list_attachments(
    conversation_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
) -> list[AttachmentResponse]:
    get_owned_conversation(conversations, workspace.id, conversation_id)
    return attachments.list_current_for_conversation(workspace.id, conversation_id)


@router.get("/{conversation_id}/workspace-attachments", response_model=list[AttachmentResponse])
def list_workspace_attachments(
    conversation_id: UUID,
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    conversations: ConversationRepository = Depends(get_conversation_repository),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
) -> list[AttachmentResponse]:
    get_owned_conversation(conversations, workspace.id, conversation_id)
    return attachments.list_workspace_for_conversation(workspace.id)


@workspace_attachment_router.get("/current/attachments", response_model=list[AttachmentResponse])
def list_current_workspace_attachments(
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
) -> list[AttachmentResponse]:
    return attachments.list_workspace_for_conversation(workspace.id)


@workspace_attachment_router.post(
    "/current/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_workspace_attachment(
    file: UploadFile = File(...),
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
    storage: ObjectStorage = Depends(get_object_storage),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> AttachmentResponse:
    return await _create_uploaded_attachment(
        file=file,
        workspace=workspace,
        conversation_id=None,
        scope="workspace",
        attachments=attachments,
        storage=storage,
        embedding_provider=embedding_provider,
    )


async def _create_uploaded_attachment(
    *,
    file: UploadFile,
    workspace: AnonymousWorkspace,
    conversation_id: UUID | None,
    scope: str,
    attachments: AttachmentRepository,
    storage: ObjectStorage,
    embedding_provider: EmbeddingProvider,
) -> AttachmentResponse:
    filename = validate_filename(file.filename)
    content = await file.read()
    attachment_id = uuid4()
    owner_key = str(conversation_id) if conversation_id is not None else "workspace"
    storage_key = f"{workspace.id}/{owner_key}/{attachment_id}/{filename}"
    attachment = attachments.create(
        id=attachment_id,
        workspace_id=workspace.id,
        conversation_id=conversation_id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        storage_key=storage_key,
        scope=scope,
        status="uploaded",
    )
    try:
        storage.put(storage_key, content)
    except Exception as error:  # noqa: BLE001 - retain a visible failed card
        return attachments.update(
            attachment, status="failed", status_message=f"文件保存失败：{error}"
        )
    return process_attachment(
        attachment=attachment,
        content=content,
        repository=attachments,
        embedding_provider=embedding_provider,
    )
