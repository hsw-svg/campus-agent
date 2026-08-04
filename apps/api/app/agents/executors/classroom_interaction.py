"""Teacher classroom interaction executor.

The executor owns the stage-7 modes that share the classroom interaction
agent: activity-package generation, deterministic observation analysis, and
post-class summary generation.
"""

from dataclasses import replace
import json
import re

from app.agents.contracts import AgentArtifact, AgentRequest, AgentResult
from app.agents.executors.generic_chat import GenericChatExecutor
from app.core.errors import AppError
from app.integrations.llm.providers import ChatProvider
from app.skills.classroom_activity import ClassroomActivityPackageSkill
from app.skills.classroom_observation import ClassroomObservationSkill, observation_data
from app.skills.classroom_summary import ClassroomSummarySkill
from app.skills.output_validation import OutputValidationSkill


class ClassroomInteractionExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.chat = GenericChatExecutor(provider)
        self.observation = ClassroomObservationSkill()
        self.activity = ClassroomActivityPackageSkill()
        self.summary = ClassroomSummarySkill()
        self.validator = OutputValidationSkill()

    async def execute(self, request: AgentRequest) -> AgentResult:
        if _is_summary_request(request.content):
            return await self._execute_summary(request)

        # Observation is checked before package generation so a teacher's
        # explicit anonymous counts can never be mistaken for model input.
        if _contains_option_counts(request.content):
            return await self._execute_observation(request)
        if _is_activity_package_request(request.content):
            return await self._execute_activity_package(request)

        result = await self.chat.execute(request)
        return replace(result, text=self.validator.run(result.text))

    async def _execute_observation(self, request: AgentRequest) -> AgentResult:
        observation = self.observation.run(request.content)
        data = {
            "scope": "class",
            "counts": observation.counts,
            "total": observation.total,
            "ratios": observation.ratios,
        }
        artifact_data = observation_data(observation)
        if observation.status == "needs_confirmation":
            text = (
                "课堂观察统计需要确认后才能继续。\n\n"
                + "\n".join(f"- {item}" for item in observation.ambiguities)
                + "\n\n请确认选项人数对应的活动或修正总人数。"
            )
            return AgentResult(
                text=text,
                structured_data=artifact_data,
                artifact=AgentArtifact(
                    type="classroom_observation",
                    title="课堂观察待确认",
                    content=text,
                    data=artifact_data,
                ),
                validation={"valid": False, "status": "needs_confirmation"},
            )

        statistics_message = {
            "role": "system",
            "content": (
                "课堂观察统计已由程序计算。只能使用以下统计解释共同误区和教学动作，"
                "不得修改人数、比例或推断个体："
                + json.dumps(data, ensure_ascii=False)
            ),
        }
        context = replace(
            request.context,
            messages=(*request.context.messages, statistics_message),
        )
        result = await self.chat.execute(replace(request, context=context))
        text = self.validator.run(result.text)
        return AgentResult(
            text=text,
            structured_data=data,
            citations=result.citations,
            artifact=AgentArtifact(
                type="classroom_observation",
                title="课堂观察分析",
                content=text,
                data=artifact_data,
            ),
        )

    async def _execute_activity_package(self, request: AgentRequest) -> AgentResult:
        missing_inputs = _missing_activity_inputs(request)
        if missing_inputs:
            raise AppError(
                code="classroom_activity_input_incomplete",
                message="生成课堂互动前请补充必要输入。",
                status_code=422,
                details={"missing_inputs": missing_inputs},
            )
        duration = _requested_duration(request.content)
        if duration is None:
            raise AppError(
                code="classroom_activity_input_incomplete",
                message="请提供本节课课堂互动的总时长（分钟）。",
                status_code=422,
                details={"missing_inputs": ["总时长"]},
            )
        prompt = {
            "role": "system",
            "content": (
                "你是课堂互动活动包设计助手。请根据用户的主题、教学目标、总时长和当前允许的资料生成活动包。"
                "只输出 JSON，不要 Markdown。顶层字段为 topic、objectives、activities；"
                "每个 activity 包含 title、type、duration_minutes、objective、prompt、options、answer、"
                "explanation、common_misconceptions、teacher_prompt、differentiated_hints、rubric、branches。"
                "type 只能是 diagnostic、multiple_choice、true_false、discussion、case；"
                "选择题必须有 options 和唯一 answer，判断题 answer 必须是 true/false，"
                "诊断题、讨论题和案例任务必须有非空 rubric。不要生成学生个体信息。"
                f"总时长上限为 {duration} 分钟。"
            ),
        }
        context = replace(request.context, messages=(prompt, *request.context.messages))
        result = await self.chat.execute(replace(request, context=context))
        package = self.activity.run((result.text, duration))
        data = package["data"]
        markdown = self.validator.run(package["markdown"])
        return AgentResult(
            text=markdown,
            structured_data=data,
            citations=result.citations,
            validation=data["validation"],
            warnings=package["warnings"],
            artifact=AgentArtifact(
                type="classroom_activity_package",
                title="课堂互动活动包",
                content=markdown,
                data=data,
            ),
        )

    async def _execute_summary(self, request: AgentRequest) -> AgentResult:
        # ``prompt`` validates the explicit artifact selection before any model
        # call, so a summary cannot silently use the conversation transcript.
        prompt = {"role": "system", "content": self.summary.prompt(request.context.selected_artifacts)}
        context = replace(request.context, messages=(prompt,), sources=(), attachment_text="")
        result = await self.chat.execute(replace(request, context=context))
        data = self.summary.parse(result.text, request.context.selected_artifacts)
        data["source_artifact_ids"] = [str(item.id) for item in request.context.selected_artifacts]
        markdown = self.validator.run(self.summary.markdown(data))
        return AgentResult(
            text=markdown,
            structured_data=data,
            citations=result.citations,
            artifact=AgentArtifact(
                type="classroom_summary",
                title="课后课堂总结",
                content=markdown,
                data=data,
            ),
        )


def _contains_option_counts(content: str) -> bool:
    return bool(
        re.search(
            r"\d+\s*人?\s*(?:选|选择|投|投给|choose|chose)?\s*[A-D]\b|"
            r"\b[A-D]\s*(?:选项)?\s*(?:有|为|是)?\s*[:：=]?\s*\d+\s*人?",
            content,
            re.IGNORECASE,
        )
    )


def _is_activity_package_request(content: str) -> bool:
    return any(
        term in content for term in ("活动包", "活动序列", "设计课堂互动", "生成课堂互动")
    )


def _is_summary_request(content: str) -> bool:
    return any(term in content for term in ("课后总结", "课堂总结", "课堂复盘"))


def _requested_duration(content: str) -> int | None:
    matches = re.findall(
        r"(?:总时长|课堂时长|时长|用时)\s*[:：=]?\s*(\d+)\s*(?:分钟|min|minutes)?|"
        r"(\d+)\s*(?:分钟|min|minutes)",
        content,
        re.IGNORECASE,
    )
    values = [int(item) for match in matches for item in match if item]
    return values[0] if values else None


def _missing_activity_inputs(request: AgentRequest) -> list[str]:
    content = request.content
    missing: list[str] = []
    if not re.search(r"(?:教学主题|主题|topic|内容|关于)\s*[:：=]?\s*\S+", content, re.IGNORECASE):
        missing.append("教学主题")
    if not re.search(
        r"(?:教学目标|本节课目标|目标|objective|学会|掌握|理解)\s*[:：=]?\s*\S+",
        content,
        re.IGNORECASE,
    ):
        missing.append("本节课目标")
    has_learning_summary = any(
        artifact.type == "learning_analysis" for artifact in request.context.selected_artifacts
    )
    if (
        not request.context.attachment_text.strip()
        and not has_learning_summary
        and not request.allow_empty_materials
    ):
        missing.append("课程资料")
    return missing
