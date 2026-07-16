from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol


class ChatProvider(Protocol):
    @property
    def is_configured(self) -> bool: ...

    def stream_reply(
        self, messages: Sequence[dict[str, str]]
    ) -> AsyncIterator[str]: ...


@dataclass(frozen=True)
class OpenAICompatibleChatProvider:
    base_url: str
    api_key: str
    model: str

    @property
    def is_configured(self) -> bool:
        return all((self.base_url.strip(), self.api_key.strip(), self.model.strip()))

    async def stream_reply(
        self, messages: Sequence[dict[str, str]]
    ) -> AsyncIterator[str]:
        """Yield assistant text deltas from an OpenAI-compatible chat endpoint.

        The OpenAI client is imported lazily so the module stays importable, and
        the health check stays cheap, even when no chat backend is configured.
        """

        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        stream = await client.chat.completions.create(
            model=self.model,
            messages=list(messages),
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None)
            if text:
                yield text

    async def classify_route(self, messages: list[dict[str, str]]) -> str:
        """Return one JSON routing decision from an OpenAI-compatible model."""

        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        response = await client.chat.completions.create(
            model=self.model,
            messages=list(messages),
            temperature=0,
            response_format={"type": "json_object"},
        )
        if not response.choices:
            raise ValueError("route classifier returned no choices")
        content = response.choices[0].message.content
        if not content:
            raise ValueError("route classifier returned empty content")
        return content
