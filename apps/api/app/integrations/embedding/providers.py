from dataclasses import dataclass
from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def is_configured(self) -> bool: ...


@dataclass(frozen=True)
class OpenAICompatibleEmbeddingProvider:
    base_url: str
    api_key: str
    model: str

    @property
    def is_configured(self) -> bool:
        return all((self.base_url.strip(), self.api_key.strip(), self.model.strip()))
