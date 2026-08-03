"""Render a normalised slide_deck payload with a registered source PPTX template."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.skills.pptx_templates.catalog import get_template
from app.skills.pptx_templates.renderer import render_template_deck


@dataclass(frozen=True)
class ExportedBinaryArtifact:
    content: bytes
    media_type: str
    extension: str


class SlideDeckPptxSkill:
    id = "slide_deck_pptx"
    version = "3"
    input_type = "dict"
    output_type = "ExportedBinaryArtifact"
    error_codes = ("pptx_template_manifest_invalid", "pptx_template_render_failed")
    has_side_effects = False
    can_access_workspace = False

    def run(self, data: dict[str, Any]) -> ExportedBinaryArtifact:
        template = get_template(str(data.get("template_id") or "").strip() or None)
        content = render_template_deck(template, data)
        return ExportedBinaryArtifact(
            content=content,
            media_type=(
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ),
            extension="pptx",
        )
