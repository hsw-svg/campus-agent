from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict

from app.api.courses import get_course_repository, get_owned_course
from app.attachments.dependencies import get_attachment_repository, get_object_storage
from app.attachments.parsing import MAX_ATTACHMENT_BYTES, validate_filename
from app.attachments.repositories import AttachmentRepository

from app.core.errors import AppError
from app.integrations.embedding.providers import EmbeddingProvider
from app.integrations.storage.base import ObjectStorage
from app.services.attachments import process_attachment
from app.integrations.deeptutor.client import DeepTutorClient, DeepTutorError, course_knowledge_base_name
from app.services.conversations import get_owned_conversation
from app.repositories.courses import CourseRepository
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
    course_id: UUID | None
    filename: str
    content_type: str
    size_bytes: int
    scope: str
    status: str
    status_message: str | None
    knowledge_base_name: str | None
    knowledge_base_status: str | None
    knowledge_base_task_id: str | None
    knowledge_base_message: str | None
    extracted_chars: int
    created_at: datetime
    updated_at: datetime


@router.post(
    "/{conversation_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    request: Request,
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
        course_id=conversation.course_id,
        attachments=attachments,
        storage=storage,
        embedding_provider=embedding_provider,
        deeptutor_client=request.app.state.deeptutor_client,
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
    conversation = get_owned_conversation(conversations, workspace.id, conversation_id)
    return attachments.list_workspace_for_conversation(workspace.id, conversation.course_id)


@workspace_attachment_router.get("/current/attachments", response_model=list[AttachmentResponse])
def list_current_workspace_attachments(
    course_id: UUID | None = Query(None),
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    courses: CourseRepository = Depends(get_course_repository),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
) -> list[AttachmentResponse]:
    if course_id is not None:
        get_owned_course(courses, workspace.id, course_id)
    return attachments.list_workspace_for_conversation(workspace.id, course_id)


@workspace_attachment_router.post(
    "/current/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_workspace_attachment(
    request: Request,
    file: UploadFile = File(...),
    course_id: UUID | None = Query(None),
    workspace: AnonymousWorkspace = Depends(get_current_workspace),
    courses: CourseRepository = Depends(get_course_repository),
    attachments: AttachmentRepository = Depends(get_attachment_repository),
    storage: ObjectStorage = Depends(get_object_storage),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> AttachmentResponse:
    if course_id is not None:
        get_owned_course(courses, workspace.id, course_id)
    return await _create_uploaded_attachment(
        file=file,
        workspace=workspace,
        conversation_id=None,
        scope="workspace",
        course_id=course_id,
        attachments=attachments,
        storage=storage,
        embedding_provider=embedding_provider,
        deeptutor_client=request.app.state.deeptutor_client,
    )


async def _create_uploaded_attachment(
    *,
    file: UploadFile,
    workspace: AnonymousWorkspace,
    conversation_id: UUID | None,
    scope: str,
    course_id: UUID | None = None,
    attachments: AttachmentRepository,
    storage: ObjectStorage,
    embedding_provider: EmbeddingProvider,
    deeptutor_client: DeepTutorClient,
) -> AttachmentResponse:
    filename = validate_filename(file.filename)
    content = await file.read(MAX_ATTACHMENT_BYTES + 1)
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise AppError(
            code="attachment_too_large",
            message="The attachment exceeds the 25 MB limit.",
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        )
    attachment_id = uuid4()
    owner_key = str(conversation_id) if conversation_id is not None else "workspace"
    storage_key = f"{workspace.id}/{owner_key}/{attachment_id}/{filename}"
    attachment = attachments.create(
        id=attachment_id,
        workspace_id=workspace.id,
        conversation_id=conversation_id,
        course_id=course_id,
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
    processed = process_attachment(
        attachment=attachment,
        content=content,
        repository=attachments,
        embedding_provider=embedding_provider,
    )
    if scope != "workspace" or course_id is None:
        return processed
    knowledge_base_name = course_knowledge_base_name(str(course_id))
    if processed.status == "failed":
        return attachments.update(
            processed,
            knowledge_base_name=knowledge_base_name,
            knowledge_base_status="failed",
            knowledge_base_message="教材未完成解析，知识库构建未启动。",
        )
    attachments.update(
        processed,
        knowledge_base_name=knowledge_base_name,
        knowledge_base_status="syncing",
        knowledge_base_message="教材知识库任务正在提交。",
    )
    try:
        result = await deeptutor_client.sync_course_material(
            course_id=str(course_id),
            filename=filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    except DeepTutorError as error:
        unavailable = error.code == "deeptutor_unavailable"
        return attachments.update(
            processed,
            knowledge_base_status="unavailable" if unavailable else "failed",
            knowledge_base_message=(
                "教材已绑定课程，本地检索可用；教材知识库服务暂不可用。"
                if unavailable
                else "教材已绑定课程，本地检索可用；教材知识库任务提交失败。"
            ),
        )
    return attachments.update(
        processed,
        knowledge_base_name=str(result["knowledge_base_name"]),
        knowledge_base_status="queued",
        knowledge_base_task_id=str(result["task_id"]),
        knowledge_base_message="教材已绑定课程，知识库正在构建。",
    )
