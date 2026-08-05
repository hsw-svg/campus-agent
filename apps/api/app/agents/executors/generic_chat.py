from collections.abc import AsyncIterator, Sequence

from app.agents.contracts import (
    AgentExecutionEvent,
    AgentRequest,
    AgentResult,
    delta_event,
    progress_event,
    result_event,
)
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
        deltas: list[str] = []
        async for event in self.stream(request, response_format=response_format):
            if event.type == "delta" and event.text:
                deltas.append(event.text)
        return AgentResult(text="".join(deltas), citations=request.context.sources)

    async def stream(
        self,
        request: AgentRequest,
        *,
        response_format: dict | None = None,
    ) -> AsyncIterator[AgentExecutionEvent]:
        if not self.provider.is_configured:
            raise RuntimeError("chat_model_unconfigured")

        yield progress_event(
            step_id="model-generation",
            phase="model",
            state="active",
            label="正在生成回复",
        )
        messages = _as_messages(request.context.messages)
        stream = (
            self.provider.stream_reply(messages)
            if response_format is None
            else self.provider.stream_reply(
                messages,
                response_format=response_format,
            )
        )
        deltas: list[str] = []
        async for delta in stream:
            if not delta:
                continue
            deltas.append(delta)
            yield delta_event(delta)
        yield progress_event(
            step_id="model-generation",
            phase="model",
            state="completed",
            label="回复生成完成",
            count=len(deltas),
        )
        yield result_event(AgentResult(text="".join(deltas), citations=request.context.sources))


def _as_messages(messages: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    return list(messages)
