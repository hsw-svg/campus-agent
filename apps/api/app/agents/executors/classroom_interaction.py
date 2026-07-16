"""Teacher classroom interaction executor with deterministic observation math."""

from dataclasses import replace
import json

from app.agents.contracts import AgentArtifact, AgentContext, AgentRequest, AgentResult
from app.agents.executors.generic_chat import GenericChatExecutor
from app.integrations.llm.providers import ChatProvider
from app.skills.classroom_observation import ClassroomObservationSkill
from app.skills.output_validation import OutputValidationSkill


class ClassroomInteractionExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.chat = GenericChatExecutor(provider)
        self.observation = ClassroomObservationSkill()
        self.validator = OutputValidationSkill()

    async def execute(self, request: AgentRequest) -> AgentResult:
        if not _contains_option_counts(request.content):
            result = await self.chat.execute(request)
            return replace(result, text=self.validator.run(result.text))

        observation = self.observation.run(request.content)
        data = {
            "scope": "class",
            "counts": observation.counts,
            "total": observation.total,
            "ratios": observation.ratios,
        }
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
                data=data,
            ),
        )


def _contains_option_counts(content: str) -> bool:
    return any(character.isdigit() for character in content) and any(
        token in content.upper() for token in ("A", "B", "C", "D", "选")
    )
