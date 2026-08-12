from dataclasses import dataclass


@dataclass(frozen=True)
class CourseLearningContext:
    """Server-owned course and chapter facts available to student agents."""

    course_id: str
    course_name: str
    description: str | None
    category: str | None
    teacher_name: str | None
    chapter_id: str | None
    chapter_title: str | None
    chapter_summary: str | None
    knowledge_points: tuple[str, ...]


def course_context_prompt(context: CourseLearningContext) -> str:
    lines = [
        "当前课程上下文（由服务端课程中心提供）：",
        f"- 课程：{context.course_name}",
    ]
    if context.category:
        lines.append(f"- 课程类别：{context.category}")
    if context.teacher_name:
        lines.append(f"- 任课教师：{context.teacher_name}")
    if context.description:
        lines.append(f"- 课程简介：{context.description}")
    if context.chapter_title:
        lines.append(f"- 当前章节：{context.chapter_title}")
    if context.chapter_summary:
        lines.append(f"- 章节摘要：{context.chapter_summary}")
    if context.knowledge_points:
        lines.append(f"- 章节知识点：{'、'.join(context.knowledge_points)}")
    lines.append(
        "可依据以上课程元数据说明课程范围、章节目标和基础概念。若没有教材引用，"
        "不得声称回答来自教材原文，也不得编造页码、例题或教师要求。"
    )
    return "\n".join(lines)
