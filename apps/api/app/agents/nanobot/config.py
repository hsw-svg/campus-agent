"""Nanobot configuration adapter.

Builds a nanobot Config from the project's Settings, using the DeepSeek provider
configured in the environment (.env file).
"""

from __future__ import annotations

from nanobot.config.schema import (
    AgentsConfig,
    AgentDefaults,
    Config,
    ProvidersConfig,
    ProviderConfig,
)

from app.core.config import Settings


def build_nanobot_config(settings: Settings) -> Config:
    """Create a nanobot Config from the project's Settings.

    Uses the DeepSeek provider configured in the environment:
    - chat_base_url → deepseek.api_base
    - chat_api_key  → deepseek.api_key
    - chat_model    → agents.defaults.model
    """
    providers = ProvidersConfig(
        deepseek=ProviderConfig(
            api_key=settings.chat_api_key,
            api_base=settings.chat_base_url,
        )
    )

    agents = AgentsConfig(
        defaults=AgentDefaults(
            provider="deepseek",
            model=settings.chat_model,
        )
    )

    return Config(
        providers=providers,
        agents=agents,
    )
