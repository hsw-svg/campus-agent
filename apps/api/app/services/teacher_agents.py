from uuid import UUID
from collections.abc import Sequence

from app.agents.teacher.learning_analysis import LearningAnalysisResult, analyze_learning_table
from app.artifacts.models import Artifact
from app.artifacts.repositories import ArtifactRepository
from app.attachments.repositories import AttachmentRepository
from app.core.errors import AppError


def create_learning_analysis_artifact(
    *,
    workspace_id: UUID,
    conversation_id: UUID,
    attachments: AttachmentRepository,
    artifacts: ArtifactRepository,
    selected_attachment_ids: Sequence[UUID] | None = None,
) -> tuple[LearningAnalysisResult, Artifact]:
    """Run class-level analysis over explicitly selected table material."""

    selected = attachments.list_selected_for_conversation(
        workspace_id, conversation_id, selected_attachment_ids
    )
    chunks = attachments.list_chunks_for_attachments(
        workspace_id, conversation_id, [attachment.id for attachment in selected]
    )
    text = "\n".join(chunk.content for chunk in chunks)
    filename = next(
        (
            chunk.attachment.filename
            for chunk in chunks
            if chunk.attachment is not None and chunk.attachment.filename.lower().endswith((".csv", ".xlsx"))
        ),
        "",
    )
    result = analyze_learning_table(text, filename=filename)
    if not result.data["validation"]["valid"]:
        raise AppError(
            code="learning_analysis_input_invalid",
            message="The learning table is incomplete or does not use an anonymous identifier.",
            status_code=422,
            details={"errors": result.data["validation"]["errors"]},
        )
    artifact = artifacts.create(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        type="learning_analysis",
        title="班级整体学情分析",
        content=result.markdown,
        data=result.data,
        format="markdown",
    )
    return result, artifact
