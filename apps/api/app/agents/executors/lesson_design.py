from app.agents.contracts import AgentRequest, AgentResult
from app.agents.executors.generic_chat import GenericChatExecutor
from app.integrations.llm.providers import ChatProvider
from app.skills.output_validation import OutputValidationSkill


class LessonDesignExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.chat = GenericChatExecutor(provider)
        self.validator = OutputValidationSkill()

    async def execute(self, request: AgentRequest) -> AgentResult:
        result = await self.chat.execute(request)
        return AgentResult(
            text=self.validator.run(result.text),
            structured_data=result.structured_data,
            citations=result.citations,
            artifact=result.artifact,
            warnings=result.warnings,
        )
