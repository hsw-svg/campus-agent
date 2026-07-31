"""Agent specifications layered over the role-scoped legacy registry."""

from dataclasses import dataclass

from app.agents.contracts import AgentExecutorId, ContextPolicy, InputContract
from app.agents.registry import AgentDefinition, list_agents


@dataclass(frozen=True)
class AgentSpec:
    id: str
    role: str
    name: str
    description: str
    system_prompt: str
    executor_id: AgentExecutorId
    input_contract: InputContract = InputContract()
    context_policy: ContextPolicy = ContextPolicy(id="conversation")
    skills: tuple[str, ...] = ()


_SYSTEM_PROMPTS: dict[str, str] = {
    "learning_analysis": (
        "你是教师端班级整体学情分析助手。只输出班级聚合统计、共同薄弱点和教学方式与节奏建议，"
        "不得生成学生个体画像或复述匿名编号对应的原始行。"
    ),
    "lesson_design": (
        "你是教师端教案与题目生成助手。根据本节课目标和允许使用的课程资料生成可直接使用的课堂练习，"
        "不要把学情表中的学生明细当作题目依据，也不要输出学生数据。"
    ),
    "classroom_interaction": (
        "你是教师端课堂互动助手。负责生成结构化课堂互动活动包、分析匿名聚合课堂观察并生成课后总结。"
        "人数和比例由程序计算，缺失数据不得猜测；课后总结只能使用教师明确选择的活动包和观察记录。"
    ),
    "course_qa": (
        "你是学生端课程资料问答助手。只依据用户明确选择的当前学生工作区课程资料回答，"
        "不得使用未选择的上传文件、其他角色资料或学情明细；资料不足时明确说明。"
        "必须只输出符合约定字段的 JSON，不要输出 Markdown。"
    ),
    "personal_tutor": (
        "你是学生端个性化辅导助手。只依据用户明确选择的当前学生工作区错题、作业或薄弱点材料，"
        "解释概念、指出错误并给出练习；不得臆造题目、成绩、资料事实或使用其他角色资料。"
        "必须只输出符合约定字段的 JSON，不要输出 Markdown。"
    ),
    "resume_helper": (
        "你是学生端简历优化助手。只使用学生明确选择的当前简历和后端提供的本人课程学习证据，"
        "不得使用其他工作区或角色资料，不得虚构经历、证书、成绩、技能或量化结果。"
        "必须只输出符合约定字段的 JSON，不要输出 Markdown。"
    ),
    "meeting_minutes": (
        "你是行政端会议纪要助手。只整理当前行政工作区和用户明确选择的资料，以及用户本次提供的会议内容。"
        "没有证据的负责人、日期、决议不得填写，使用 null；必须只输出约定字段的 JSON，不要输出 Markdown。"
    ),
    "todo_breakdown": (
        "你是行政端待办拆解助手。只依据当前行政工作区、用户明确选择的资料和本次任务内容拆解行动项。"
        "不得臆造负责人、日期、优先级或事实；没有证据时使用 null；必须只输出约定字段的 JSON，不要输出 Markdown。"
    ),
    "course_iteration": (
        "你是教师端课程迭代助手。当用户要求生成课件/幻灯/PPT/演示文稿时，需要综合课程学情、"
        "课堂总结、批改反馈以及联网检索的行业与岗位信息，严格按 slide_deck JSON schema 输出"
        "（字段：topic/audience/objective/duration_minutes/context_signals/slides/sources；"
        "slides[].layout ∈ title|bullets|two_column|callout|summary；"
        "slides[].media 可含 0~2 个多媒体建议，字段包括 kind∈image|video|gif|embed|animation、"
        "url/title/caption/placement∈top|right|left|background|inline、autoplay/loop/muted/start_ms/end_ms；"
        "当知识点适合动态演示、操作演示、情境播放时主动插入适当媒体；"
        "至少一页 citations 引用 industry_updates），只输出 JSON。对非幻灯请求，使用简体中文给出课程迭代建议。"
    ),
}


def agent_spec_from_definition(role: str, definition: AgentDefinition) -> AgentSpec:
    return AgentSpec(
        id=definition.id,
        role=role,
        name=definition.name,
        description=definition.description,
        system_prompt=_SYSTEM_PROMPTS.get(
            definition.id,
            f"你是{definition.name}。只处理当前角色允许的任务，并明确说明资料不足。",
        ),
        executor_id={
            "learning_analysis": "learning_analysis",
            "lesson_design": "lesson_design",
            "classroom_interaction": "classroom_interaction",
            "course_qa": "course_qa",
            "personal_tutor": "personal_tutor",
            "resume_helper": "resume_helper",
            "meeting_minutes": "meeting_minutes",
            "todo_breakdown": "todo_breakdown",
            "course_iteration": "course_iteration",
        }.get(definition.id, "generic_chat"),
        input_contract=InputContract(
            requires_attachments=definition.id in {
                "learning_analysis",
                "course_qa",
                "personal_tutor",
                "resume_helper",
            },
            accepted_attachment_types=("text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            if definition.id == "learning_analysis"
            else (),
        ),
        context_policy=ContextPolicy(
            id={
                "learning_analysis": "selected_learning_tables",
                "lesson_design": "selected_course_materials",
                "classroom_interaction": "selected_classroom_materials",
                "course_qa": "selected_course_materials",
                "personal_tutor": "selected_student_support_materials",
                "resume_helper": "selected_student_resume",
                "meeting_minutes": "selected_admin_materials",
                "todo_breakdown": "selected_admin_materials",
            }.get(definition.id, "conversation"),
            requires_explicit_attachments=definition.id in {
                "learning_analysis",
                "course_iteration",
                "teaching_report",
                "course_qa",
                "personal_tutor",
                "resume_helper",
            },
            allow_workspace_attachments=definition.id in {
                "learning_analysis",
                "course_iteration",
                "teaching_report",
                "course_qa",
                "personal_tutor",
                "resume_helper",
                "meeting_minutes",
                "todo_breakdown",
            },
            allow_implicit_conversation_attachments=definition.id not in {
                "course_qa",
                "personal_tutor",
                "resume_helper",
                "meeting_minutes",
                "todo_breakdown",
            },
            exclude_learning_details=definition.id != "learning_analysis",
            allow_raw_row_sources=definition.id not in {
                "learning_analysis",
                "course_qa",
                "personal_tutor",
                "meeting_minutes",
                "todo_breakdown",
            },
        ),
        skills={
            "learning_analysis": ("table_parser", "learning_statistics", "output_validation", "artifact_exporter"),
            "classroom_interaction": (
                "classroom_activity_package",
                "classroom_observation_parser",
                "classroom_summary",
                "output_validation",
                "artifact_exporter",
            ),
            "lesson_design": ("output_validation",),
            "course_qa": ("output_validation", "artifact_exporter"),
            "personal_tutor": ("output_validation", "artifact_exporter"),
            "resume_helper": ("output_validation", "artifact_exporter"),
            "meeting_minutes": ("output_validation", "artifact_exporter"),
            "todo_breakdown": ("output_validation", "artifact_exporter"),
            "course_iteration": (
                "slide_deck_json",
                "slide_deck_markdown",
                "artifact_exporter",
            ),
        }.get(definition.id, ()),
    )


def list_agent_specs(role: str) -> tuple[AgentSpec, ...]:
    return tuple(agent_spec_from_definition(role, item) for item in list_agents(role))


def get_agent_spec(role: str, agent_id: str) -> AgentSpec | None:
    return next((item for item in list_agent_specs(role) if item.id == agent_id), None)
