from collections.abc import Sequence

from app.agents.contracts import AgentRequest, AgentResult
from app.integrations.llm.providers import ChatProvider


class GenericChatExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.provider = provider

    async def execute(
        self,
        request: AgentRequest,
        *,
        response_format: dict | None = None,
    ) -> AgentResult:
        if not self.provider.is_configured:
            raise RuntimeError("chat_model_unconfigured")
        deltas: list[str] = []
        messages = _as_messages(request.context.messages)
        stream = (
            self.provider.stream_reply(messages)
            if response_format is None
            else self.provider.stream_reply(
                messages,
                response_format=response_format,
            )
        )
        async for delta in stream:
            deltas.append(delta)
        return AgentResult(text="".join(deltas), citations=request.context.sources)


def _as_messages(messages: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    return list(messages)
