from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def is_configured(self) -> bool: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class OpenAICompatibleEmbeddingProvider:
    base_url: str
    api_key: str
    model: str

    @property
    def is_configured(self) -> bool:
        return all((self.base_url.strip(), self.api_key.strip(), self.model.strip()))

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return embeddings from the configured OpenAI-compatible endpoint."""

        from openai import OpenAI

        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        response = client.embeddings.create(model=self.model, input=list(texts))
        return [list(item.embedding) for item in sorted(response.data, key=lambda item: item.index)]
