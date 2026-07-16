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
        }.get(definition.id, "generic_chat"),
        input_contract=InputContract(
            requires_attachments=definition.id == "learning_analysis",
            accepted_attachment_types=("text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            if definition.id == "learning_analysis"
            else (),
        ),
        context_policy=ContextPolicy(
            id={
                "learning_analysis": "selected_learning_tables",
                "lesson_design": "selected_course_materials",
                "classroom_interaction": "selected_classroom_materials",
            }.get(definition.id, "conversation"),
            requires_explicit_attachments=definition.id in {
                "learning_analysis",
                "course_iteration",
                "teaching_report",
            },
            allow_workspace_attachments=definition.id in {
                "learning_analysis",
                "course_iteration",
                "teaching_report",
            },
            exclude_learning_details=definition.id != "learning_analysis",
            allow_raw_row_sources=definition.id != "learning_analysis",
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
        }.get(definition.id, ()),
    )


def list_agent_specs(role: str) -> tuple[AgentSpec, ...]:
    return tuple(agent_spec_from_definition(role, item) for item in list_agents(role))


def get_agent_spec(role: str, agent_id: str) -> AgentSpec | None:
    return next((item for item in list_agent_specs(role) if item.id == agent_id), None)
