from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings sourced exclusively from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Campus Agent API"
    database_url: str = "postgresql+psycopg://campus_agent:campus_agent@localhost:5432/campus_agent"
    local_storage_root: Path = Path("storage")
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    chat_base_url: str = ""
    chat_api_key: str = ""
    chat_model: str = ""
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""

    @property
    def chat_is_configured(self) -> bool:
        return all((self.chat_base_url.strip(), self.chat_api_key.strip(), self.chat_model.strip()))

    @property
    def embedding_is_configured(self) -> bool:
        return all(
            (
                self.embedding_base_url.strip(),
                self.embedding_api_key.strip(),
                self.embedding_model.strip(),
            )
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
