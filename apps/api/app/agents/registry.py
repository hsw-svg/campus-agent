"""A read-only whitelist mapping each role to the agents it may use.

Stage 3 only needs this registry to populate the agent selector and to reject
forged ``agent_id`` values that do not belong to the current role. The actual
routing and execution logic arrives in later stages; here every agent shares a
single conversational behaviour so the unified shell can be demonstrated
end to end without leaking one role's capabilities into another.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    description: str


# The sentinel selection used by the shell when no specific agent is chosen.
AUTO_AGENT_ID = "auto"

_ROLE_AGENTS: dict[str, tuple[AgentDefinition, ...]] = {
    "student": (
        AgentDefinition("course_qa", "课程资料问答", "基于本人上传的教材与讲义进行问答。"),
        AgentDefinition("personal_tutor", "个性化答疑", "根据本人错题与薄弱点进行讲解。"),
        AgentDefinition("practice_helper", "练习助手", "生成分层练习、解析与学习建议。"),
        AgentDefinition("resume_helper", "简历助手", "分析简历、改写经历并生成模拟面试问题。"),
        AgentDefinition("speaking_practice", "口语练习", "围绕指定场景进行对话与表达建议。"),
        AgentDefinition("study_planner", "学习规划", "根据本人目标与时间生成学习计划。"),
    ),
    "teacher": (
        AgentDefinition("grading", "作业批改", "基于题目与参考答案生成评分建议与评语。"),
        AgentDefinition("learning_analysis", "学情分析", "对匿名成绩表生成统计、薄弱点与教学建议。"),
        AgentDefinition("classroom_interaction", "课堂互动助手", "生成互动方案并分析课堂现象。"),
        AgentDefinition("course_iteration", "课程迭代", "结合教材与学情生成课件更新建议。"),
        AgentDefinition("lesson_design", "教案与题目生成", "生成教案、互动题与评分量规。"),
        AgentDefinition("teaching_report", "教学报告", "汇总教师工作空间中明确选择的材料生成报告。"),
    ),
    "admin": (
        AgentDefinition("notice_writer", "通知生成与润色", "生成并润色行政通知。"),
        AgentDefinition("meeting_minutes", "会议纪要整理", "整理会议记录为规范纪要。"),
        AgentDefinition("summary", "材料摘要", "提取材料要点并生成摘要。"),
        AgentDefinition("todo_breakdown", "待办拆解", "将材料拆解为可执行的待办项。"),
        AgentDefinition("text_cleanup", "表格与文本规整", "规整表格与文本格式。"),
        AgentDefinition("format_check", "公文格式检查", "检查公文格式并提出修订建议。"),
    ),
}


def list_agents(role: str) -> tuple[AgentDefinition, ...]:
    """Return the agents available to a role, never crossing role boundaries."""

    return _ROLE_AGENTS.get(role, ())


def is_agent_available_for_role(role: str, agent_id: str) -> bool:
    """Report whether an agent id is on the whitelist for the given role."""

    if agent_id == AUTO_AGENT_ID:
        return True
    return any(agent.id == agent_id for agent in _ROLE_AGENTS.get(role, ()))
