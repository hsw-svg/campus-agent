"""Render a normalised slide_deck dict to a .pptx binary via python-pptx."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExportedBinaryArtifact:
    content: bytes
    media_type: str
    extension: str


class SlideDeckPptxSkill:
    id = "slide_deck_pptx"
    version = "1"
    input_type = "dict"
    output_type = "ExportedBinaryArtifact"
    error_codes = ()
    has_side_effects = False
    can_access_workspace = False

    def run(self, data: dict[str, Any]) -> ExportedBinaryArtifact:
        from pptx import Presentation  # imported lazily

        presentation = Presentation()
        layouts = presentation.slide_layouts
        title_layout = layouts[0]
        content_layout = layouts[1] if len(layouts) > 1 else layouts[0]
        two_col_layout = layouts[3] if len(layouts) > 3 else content_layout

        topic = str(data.get("topic") or "未命名课件").strip()
        audience = str(data.get("audience") or "").strip()
        objective = str(data.get("objective") or "").strip()

        cover = presentation.slides.add_slide(title_layout)
        _set_title(cover, topic)
        subtitle_bits: list[str] = []
        if audience:
            subtitle_bits.append(audience)
        if objective:
            subtitle_bits.append(objective)
        if subtitle_bits:
            _set_subtitle(cover, " · ".join(subtitle_bits))

        for slide in data.get("slides") or []:
            layout_key = slide.get("layout") or "bullets"
            if layout_key == "title":
                pptx_slide = presentation.slides.add_slide(title_layout)
                _set_title(pptx_slide, str(slide.get("title") or ""))
                if slide.get("subtitle"):
                    _set_subtitle(pptx_slide, str(slide["subtitle"]))
            elif layout_key == "two_column" and slide.get("columns"):
                pptx_slide = presentation.slides.add_slide(two_col_layout)
                _set_title(pptx_slide, str(slide.get("title") or ""))
                _fill_two_column(pptx_slide, slide.get("columns") or [])
            else:
                pptx_slide = presentation.slides.add_slide(content_layout)
                _set_title(pptx_slide, str(slide.get("title") or ""))
                bullets = list(slide.get("bullets") or [])
                if layout_key == "callout" and bullets:
                    bullets = [f"重点：{bullets[0]}"] + bullets[1:]
                if slide.get("key_points"):
                    bullets = bullets + ["重点：" + "、".join(slide["key_points"])]
                _fill_body(pptx_slide, bullets)

            notes = str(slide.get("notes") or "").strip()
            media = list(slide.get("media") or [])
            media_notes = _build_media_notes(media)
            combined_notes = "\n".join(filter(None, [notes, media_notes])).strip()
            if combined_notes:
                pptx_slide.notes_slide.notes_text_frame.text = combined_notes

        buffer = io.BytesIO()
        presentation.save(buffer)
        return ExportedBinaryArtifact(
            content=buffer.getvalue(),
            media_type=(
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            ),
            extension="pptx",
        )


def _set_title(slide, text: str) -> None:
    if slide.shapes.title is not None:
        slide.shapes.title.text = text


def _set_subtitle(slide, text: str) -> None:
    for shape in slide.placeholders:
        if shape.placeholder_format.idx == 1:
            shape.text = text
            return


def _fill_body(slide, bullets: list[str]) -> None:
    body = _find_body_placeholder(slide)
    if body is None or not bullets:
        return
    text_frame = body.text_frame
    text_frame.text = bullets[0]
    for extra in bullets[1:]:
        paragraph = text_frame.add_paragraph()
        paragraph.text = extra


def _fill_two_column(slide, columns: list[dict[str, Any]]) -> None:
    placeholders = [
        shape
        for shape in slide.placeholders
        if shape.placeholder_format.idx not in (0,)
    ]
    for idx, column in enumerate(columns[:2]):
        if idx >= len(placeholders):
            break
        placeholder = placeholders[idx]
        header = column.get("title") or ""
        bullets = list(column.get("bullets") or [])
        text_frame = placeholder.text_frame
        first_line = header or (bullets.pop(0) if bullets else "")
        text_frame.text = first_line
        for bullet in bullets:
            paragraph = text_frame.add_paragraph()
            paragraph.text = bullet


def _find_body_placeholder(slide):
    for shape in slide.placeholders:
        if shape.placeholder_format.idx == 1:
            return shape
    for shape in slide.placeholders:
        if shape.placeholder_format.idx != 0:
            return shape
    return None


_MEDIA_KIND_LABELS: dict[str, str] = {
    "image": "图片",
    "video": "视频",
    "gif": "动图",
    "embed": "嵌入",
    "animation": "动画",
}

_PLACEMENT_LABELS: dict[str, str] = {
    "top": "顶部",
    "right": "右侧",
    "left": "左侧",
    "background": "背景",
    "inline": "内嵌",
}


def _build_media_notes(media: list[dict[str, Any]]) -> str:
    if not media:
        return ""
    lines: list[str] = ["[多媒体建议]"]
    for item in media:
        kind = str(item.get("kind") or "素材")
        kind_label = _MEDIA_KIND_LABELS.get(kind, kind)
        title = str(item.get("title") or item.get("alt") or "未命名素材")
        url = str(item.get("url") or "").strip()
        placement = str(item.get("placement") or "inline")
        placement_label = _PLACEMENT_LABELS.get(placement, placement)
        line = f"• {kind_label}: {title}（{placement_label}）"
        if url:
            line += f"\n  链接: {url}"
        lines.append(line)
    return "\n".join(lines)
