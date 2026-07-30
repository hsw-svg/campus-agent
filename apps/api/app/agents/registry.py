"""A read-only whitelist mapping each role to the agents it may use.

Stage 3 only needs this registry to populate the agent selector and to reject
forged ``agent_id`` values that do not belong to the current role. The actual
routing and execution logic arrives in later stages; here every agent shares a
single conversational behaviour so the unified shell can be demonstrated
end to end without leaking one role's capabilities into another.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingProfile:
    intent: str
    examples: tuple[str, ...]
    exclusions: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    description: str
    routing: RoutingProfile


def _routing(
    intent: str,
    examples: tuple[str, ...],
    exclusions: tuple[str, ...] = (),
) -> RoutingProfile:
    return RoutingProfile(intent=intent, examples=examples, exclusions=exclusions)


# The sentinel selection used by the shell when no specific agent is chosen.
AUTO_AGENT_ID = "auto"

_ROLE_AGENTS: dict[str, tuple[AgentDefinition, ...]] = {
    "student": (
        AgentDefinition(
            "course_qa",
            "课程资料问答",
            "基于本人上传的教材与讲义进行问答。",
            _routing(
                "依据用户明确选择的课程教材、讲义或笔记回答知识问题。",
                ("根据这份讲义解释牛顿第二定律", "教材里如何定义二叉树", "这段课程资料讲了什么"),
                ("不负责针对个人错题诊断", "不负责生成整套练习"),
            ),
        ),
        AgentDefinition(
            "personal_tutor",
            "个性化答疑",
            "根据本人错题与薄弱点进行讲解。",
            _routing(
                "结合学生本人的错题、作业或薄弱点进行针对性讲解与纠错。",
                ("讲讲我这道错题为什么错", "针对我的薄弱点辅导一下", "帮我分析这份作业里的错误"),
                ("不负责一般课程资料检索", "不负责长期学习日程规划"),
            ),
        ),
        AgentDefinition(
            "practice_helper",
            "练习助手",
            "生成分层练习、解析与学习建议。",
            _routing(
                "围绕知识点生成练习题、答案、解析和分层训练建议。",
                ("生成十道函数练习题", "给我一组从易到难的英语语法练习", "出几道题并附解析"),
                ("不负责批改已经提交的教师作业", "不负责生成教师教案"),
            ),
        ),
        AgentDefinition(
            "resume_helper",
            "简历助手",
            "分析简历、改写经历并生成模拟面试问题。",
            _routing(
                "分析和改写求职简历，优化项目经历并准备面试。",
                ("帮我优化这份简历", "把项目经历改得更专业", "根据简历生成模拟面试问题"),
                ("不负责普通材料摘要", "不负责学习计划"),
            ),
        ),
        AgentDefinition(
            "speaking_practice",
            "口语练习",
            "围绕指定场景进行对话与表达建议。",
            _routing(
                "围绕指定语言和场景开展口语对话练习并给出表达反馈。",
                ("陪我练习英语面试口语", "模拟一次酒店入住对话", "纠正我的英文口语表达"),
                ("不负责书面语法题生成", "不负责简历改写"),
            ),
        ),
        AgentDefinition(
            "study_planner",
            "学习规划",
            "根据本人目标与时间生成学习计划。",
            _routing(
                "根据学习目标、期限和可用时间制定阶段性学习计划。",
                ("制定六周考研复习计划", "每天两小时怎么安排 Python 学习", "帮我规划期末复习进度"),
                ("不负责单道错题讲解", "不负责课程资料事实问答"),
            ),
        ),
    ),
    "teacher": (
        AgentDefinition(
            "grading",
            "作业批改",
            "基于题目与参考答案生成评分建议与评语。",
            _routing(
                "依据题目、参考答案和学生作答进行批改、评分与评语生成。",
                ("批改这份作业并给分", "根据参考答案评价学生作答", "为这些答案生成评语"),
                ("不负责班级整体成绩统计", "不负责生成新练习"),
            ),
        ),
        AgentDefinition(
            "learning_analysis",
            "学情分析",
            "对匿名成绩表生成统计、薄弱点与教学建议。",
            _routing(
                "分析班级匿名成绩、作业或练习统计，识别共同薄弱点和教学建议。",
                ("分析这份成绩表的薄弱知识点", "总结上周测试的班级学情", "统计各章节得分率并给建议"),
                ("不负责生成课件或教案", "不负责评价单个学生身份"),
            ),
        ),
        AgentDefinition(
            "classroom_interaction",
            "课堂互动助手",
            "生成互动方案并分析课堂现象。",
            _routing(
                "设计课堂互动活动，分析匿名课堂观察，并形成课堂或课后总结。",
                ("设计一个课堂互动活动", "分析举手和选项人数", "根据课堂观察生成课后总结"),
                ("不负责完整教案", "不负责成绩表学情统计"),
            ),
        ),
        AgentDefinition(
            "course_iteration",
            "课程迭代",
            "结合教材与学情生成课件更新建议。",
            _routing(
                "结合课程资料和反馈迭代课程内容，尤其生成或修改 PPT、幻灯片和课件。",
                ("生成极限运算法则的 PPT", "根据学情更新这份课件", "把课程内容整理成演示文稿"),
                ("不负责班级成绩统计本身", "不负责仅生成课堂练习题"),
            ),
        ),
        AgentDefinition(
            "lesson_design",
            "教案与题目生成",
            "生成教案、互动题与评分量规。",
            _routing(
                "生成教案、教学设计、课堂练习、互动题和评分量规。",
                ("生成一份 Python 数组教案", "设计本节课的课堂练习", "为教学目标制作评分量规"),
                ("不负责生成 PPT 课件", "不负责分析已有成绩表"),
            ),
        ),
        AgentDefinition(
            "teaching_report",
            "教学报告",
            "汇总教师工作空间中明确选择的材料生成报告。",
            _routing(
                "汇总明确选择的教学材料、成果和反馈，形成阶段性教学报告。",
                ("生成本月教学工作报告", "汇总这些材料形成课程总结报告", "整理本学期教学成果"),
                ("不负责单次课堂观察总结", "不负责生成课件"),
            ),
        ),
    ),
    "admin": (
        AgentDefinition(
            "notice_writer",
            "通知生成与润色",
            "生成并润色行政通知。",
            _routing(
                "起草或润色面向师生和部门的行政通知。",
                ("起草一份放假通知", "润色这份会议通知", "生成活动报名通知"),
                ("不负责整理会议纪要", "不负责检查既有公文格式"),
            ),
        ),
        AgentDefinition(
            "meeting_minutes",
            "会议纪要整理",
            "整理会议记录为规范纪要。",
            _routing(
                "将会议录音转写或记录整理为议题、决议和行动项清晰的会议纪要。",
                ("把会议记录整理成纪要", "提取参会人员、议题和决议", "根据发言记录生成会议纪要"),
                ("不负责只拆解一份普通材料的待办", "不负责发布会议通知"),
            ),
        ),
        AgentDefinition(
            "summary",
            "材料摘要",
            "提取材料要点并生成摘要。",
            _routing(
                "提炼行政材料、报告或长文本的核心内容和关键要点。",
                ("总结这份材料的要点", "为这份报告生成摘要", "把长文压缩成三点结论"),
                ("不负责生成会议专用纪要", "不负责拆解执行待办"),
            ),
        ),
        AgentDefinition(
            "todo_breakdown",
            "待办拆解",
            "将材料拆解为可执行的待办项。",
            _routing(
                "从目标、方案或材料中拆解可执行任务、负责人和期限。",
                ("把这个方案拆成待办", "提取行动项并标注负责人", "生成可执行任务清单"),
                ("不负责一般内容摘要", "不负责整理完整会议纪要"),
            ),
        ),
        AgentDefinition(
            "text_cleanup",
            "表格与文本规整",
            "规整表格与文本格式。",
            _routing(
                "清理和规整杂乱文本、表格、编号、空白与基础排版。",
                ("把这张表格整理整齐", "清理这段文字的乱码和空行", "统一编号和日期格式"),
                ("不负责审查正式公文规范", "不负责改写通知内容"),
            ),
        ),
        AgentDefinition(
            "format_check",
            "公文格式检查",
            "检查公文格式并提出修订建议。",
            _routing(
                "检查公文的标题、称谓、落款、日期、层级和规范格式并提出修改建议。",
                ("检查这份公文格式", "看看通知的落款和日期是否规范", "审查标题和正文层级"),
                ("不负责从零起草通知", "不负责普通表格清理"),
            ),
        ),
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
