from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.core.errors import AppError
from app.integrations.storage.base import ObjectStorage
from app.skills.slide_deck_pptx import SlideDeckPptxSkill


class PptxSkill(Protocol):
    def run(self, data: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class ArtifactPresentation:
    object_key: str
    mime_type: str
    sha256: str
    size_bytes: int
    page_count: int

    def artifact_values(self) -> dict[str, Any]:
        return {
            "object_key": self.object_key,
            "mime_type": self.mime_type,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "page_count": self.page_count,
            "preview_status": None,
            "preview_manifest": None,
        }

    def object_keys(self) -> tuple[str, ...]:
        return (self.object_key,)


class ArtifactPresentationService:
    """Stage one authoritative PPTX derived from the semantic deck."""

    def __init__(
        self,
        storage: ObjectStorage,
        *,
        pptx_skill: PptxSkill | None = None,
    ) -> None:
        self.storage = storage
        self.pptx_skill = pptx_skill or SlideDeckPptxSkill()

    def prepare(
        self,
        normalized_deck: dict[str, Any],
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        scope_id: UUID,
    ) -> ArtifactPresentation:
        slide_ids = self._slide_ids(normalized_deck)
        prefix = f"workspaces/{workspace_id}/conversations/{conversation_id}/artifacts/{scope_id}"
        pptx_key = f"{prefix}/presentation.pptx"
        written_keys: list[str] = []

        try:
            # This is the sole semantic-deck-to-PPTX call in the operation.
            exported = self.pptx_skill.run(normalized_deck)
            if exported.media_type != (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ):
                raise AppError(
                    code="artifact_presentation_invalid",
                    message="The presentation skill returned an unexpected media type.",
                    status_code=422,
                )

            written_keys.append(pptx_key)
            self.storage.put(pptx_key, exported.content)
            stored_pptx = self.storage.get(pptx_key)

            return ArtifactPresentation(
                object_key=pptx_key,
                mime_type=exported.media_type,
                sha256=hashlib.sha256(stored_pptx).hexdigest(),
                size_bytes=len(stored_pptx),
                page_count=len(slide_ids),
            )
        except Exception:
            for key in reversed(written_keys):
                try:
                    self.storage.delete(key)
                except Exception:
                    pass
            raise

    def cleanup(self, presentation: ArtifactPresentation) -> None:
        """Best-effort removal when persistence fails after preparation."""
        for key in reversed(presentation.object_keys()):
            try:
                self.storage.delete(key)
            except Exception:
                pass

    @staticmethod
    def _slide_ids(normalized_deck: dict[str, Any]) -> tuple[str, ...]:
        slides = normalized_deck.get("slides")
        if not isinstance(slides, list) or not slides:
            raise AppError(
                code="artifact_presentation_invalid",
                message="A presentation requires at least one normalized semantic slide.",
                status_code=422,
            )
        ids = tuple(str(slide.get("id") or "").strip() for slide in slides if isinstance(slide, dict))
        if len(ids) != len(slides) or any(not slide_id for slide_id in ids) or len(set(ids)) != len(ids):
            raise AppError(
                code="artifact_presentation_invalid",
                message="Normalized semantic slides require unique, non-empty IDs.",
                status_code=422,
            )
        return ids
