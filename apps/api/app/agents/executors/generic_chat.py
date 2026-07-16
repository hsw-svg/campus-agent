from collections.abc import Sequence

from app.agents.contracts import AgentRequest, AgentResult
from app.integrations.llm.providers import ChatProvider


class GenericChatExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.provider = provider

    async def execute(self, request: AgentRequest) -> AgentResult:
        if not self.provider.is_configured:
            raise RuntimeError("chat_model_unconfigured")
        deltas: list[str] = []
        async for delta in self.provider.stream_reply(_as_messages(request.context.messages)):
            deltas.append(delta)
        return AgentResult(text="".join(deltas), citations=request.context.sources)


def _as_messages(messages: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    return list(messages)
