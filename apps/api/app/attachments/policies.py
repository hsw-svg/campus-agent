"""Policies for keeping specialist material inside its owning agent."""

from app.attachments.models import MaterialChunk


_ANONYMOUS_ID_TERMS = ("匿名编号", "匿名学号", "student_no", "student_id")
_LEARNING_TERMS = (
    "成绩",
    "得分",
    "分数",
    "满分",
    "正确率",
    "作业",
    "签到",
    "到课",
    "课堂积极性",
)


def is_learning_analysis_material(chunk: MaterialChunk) -> bool:
    """Return whether a chunk is a class learning-analysis data source.

    The upload API intentionally stays generic, so this classification is
    derived from the attachment name and parsed header/content.  It is used
    as a deny-by-default safety boundary for non-analysis agents.
    """

    attachment = chunk.attachment
    if attachment is None:
        return False
    filename = attachment.filename.lower()
    if any(term in filename for term in ("学情", "成绩", "score", "grade")):
        return True

    text = chunk.content.lower()
    has_anonymous_id = any(term in text for term in _ANONYMOUS_ID_TERMS)
    learning_field_count = sum(term in text for term in _LEARNING_TERMS)
    return has_anonymous_id and learning_field_count >= 1
