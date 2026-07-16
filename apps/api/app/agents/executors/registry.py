"""Resolve stable agent specifications to isolated executors."""

from app.agents.contracts import AgentExecutor
from app.agents.executors.classroom_interaction import ClassroomInteractionExecutor
from app.agents.executors.generic_chat import GenericChatExecutor
from app.agents.executors.learning_analysis import LearningAnalysisExecutor
from app.agents.executors.lesson_design import LessonDesignExecutor
from app.agents.specs import AgentSpec
from app.agents.specs import get_agent_spec
from app.integrations.llm.providers import ChatProvider


class AgentExecutorRegistry:
    def __init__(self, chat_provider: ChatProvider) -> None:
        self.chat_provider = chat_provider

    def resolve(self, spec_or_role: AgentSpec | str, agent_id: str | None = None) -> AgentExecutor:
        spec = (
            spec_or_role
            if isinstance(spec_or_role, AgentSpec)
            else get_agent_spec(spec_or_role, agent_id or "")
        )
        if spec is None:
            raise ValueError("AgentSpec is not registered for this role and agent")
        if spec.executor_id == "learning_analysis":
            return LearningAnalysisExecutor()
        if spec.executor_id == "lesson_design":
            return LessonDesignExecutor(self.chat_provider)
        if spec.executor_id == "classroom_interaction":
            return ClassroomInteractionExecutor(self.chat_provider)
        return GenericChatExecutor(self.chat_provider)
