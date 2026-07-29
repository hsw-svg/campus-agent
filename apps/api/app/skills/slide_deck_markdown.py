"""Render a normalised slide_deck dict into a Markdown document."""

from __future__ import annotations

from typing import Any


class SlideDeckMarkdownSkill:
    id = "slide_deck_markdown"
    version = "1"
    input_type = "dict"
    output_type = "str"
    error_codes = ()
    has_side_effects = False
    can_access_workspace = False

    def run(self, data: dict[str, Any]) -> str:
        return render(data)


def render(data: dict[str, Any]) -> str:
    lines: list[str] = []
    topic = str(data.get("topic") or "").strip() or "未命名课件"
    lines.append(f"# {topic}")
    meta_parts: list[str] = []
    audience = str(data.get("audience") or "").strip()
    if audience:
        meta_parts.append(f"面向：{audience}")
    duration = data.get("duration_minutes")
    if duration:
        meta_parts.append(f"时长：{duration} 分钟")
    objective = str(data.get("objective") or "").strip()
    if objective:
        meta_parts.append(f"目标：{objective}")
    if meta_parts:
        lines.append("")
        lines.append(" · ".join(meta_parts))

    signals = data.get("context_signals") or {}
    if any(signals.get(key) for key in ("learning_analysis", "weak_points", "classroom_summary", "grading", "job_skill_focus", "industry_updates")):
        lines.append("")
        lines.append("## 教学上下文")
        if signals.get("learning_analysis"):
            lines.append(f"- 学情摘要：{signals['learning_analysis']}")
        if signals.get("weak_points"):
            lines.append("- 薄弱点：" + "、".join(signals["weak_points"]))
        if signals.get("classroom_summary"):
            lines.append(f"- 课堂总结：{signals['classroom_summary']}")
        if signals.get("grading"):
            lines.append(f"- 批改反馈：{signals['grading']}")
        if signals.get("job_skill_focus"):
            lines.append("- 岗位技能焦点：" + "、".join(signals["job_skill_focus"]))
        if signals.get("industry_updates"):
            lines.append("- 行业信息：")
            for entry in signals["industry_updates"]:
                lines.append(f"  - [{entry.get('title') or entry.get('url')}]({entry.get('url')})")

    for slide in data.get("slides") or []:
        lines.append("")
        lines.append(f"## {slide.get('index')}. {slide.get('title') or ''}".rstrip())
        subtitle = slide.get("subtitle")
        if subtitle:
            lines.append(f"_{subtitle}_")
        layout = slide.get("layout") or "bullets"
        if layout == "two_column" and slide.get("columns"):
            for column in slide["columns"]:
                if column.get("title"):
                    lines.append(f"**{column['title']}**")
                for bullet in column.get("bullets") or []:
                    lines.append(f"- {bullet}")
        else:
            for bullet in slide.get("bullets") or []:
                lines.append(f"- {bullet}")
        if slide.get("key_points"):
            lines.append("重点：" + "、".join(slide["key_points"]))
        if slide.get("media"):
            lines.append("媒体建议：")
            for media in slide["media"]:
                label = media.get("title") or media.get("url") or media.get("kind") or "未命名素材"
                placement = media.get("placement") or "inline"
                lines.append(f"- [{label}]({media.get('url')}) · {media.get('kind')} · {placement}")
        if slide.get("notes"):
            lines.append(f"> 备注：{slide['notes']}")
        if slide.get("citations"):
            lines.append("引用：")
            for entry in slide["citations"]:
                lines.append(f"- [{entry.get('title') or entry.get('url')}]({entry.get('url')})")

    if data.get("sources"):
        lines.append("")
        lines.append("## 参考来源")
        for entry in data["sources"]:
            lines.append(f"- [{entry.get('title') or entry.get('url')}]({entry.get('url')})")

    return "\n".join(lines).rstrip() + "\n"
