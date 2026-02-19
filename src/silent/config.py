from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from .exceptions import ConfigurationError

ProviderPolicy = Literal["local_first", "online_first", "local_only", "online_only"]
OutputFormat = Literal["markdown", "text", "json"]
TimestampMode = Literal["section", "point", "none"]


@dataclass
class Settings:
    provider_policy: ProviderPolicy = "local_first"
    ollama_host: str = "http://localhost:11434"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None
    local_model: str = "qwen2.5:7b-instruct"
    online_model: str = "gpt-4.1-mini"


def load_settings(
    *,
    provider_policy: ProviderPolicy | None = None,
    local_model: str | None = None,
    online_model: str | None = None,
) -> Settings:
    settings = Settings(
        provider_policy=(
            provider_policy
            or os.getenv("VIDEO_NOTES_PROVIDER_POLICY", "local_first")
        ),
        ollama_host=os.getenv("VIDEO_NOTES_OLLAMA_HOST", "http://localhost:11434"),
        openai_base_url=os.getenv("VIDEO_NOTES_OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_api_key=os.getenv("VIDEO_NOTES_OPENAI_API_KEY"),
        local_model=local_model or os.getenv("VIDEO_NOTES_LOCAL_MODEL", "qwen2.5:7b-instruct"),
        online_model=online_model or os.getenv("VIDEO_NOTES_ONLINE_MODEL", "gpt-4.1-mini"),
    )

    allowed = {"local_first", "online_first", "local_only", "online_only"}
    if settings.provider_policy not in allowed:
        raise ConfigurationError(
            f"Invalid provider policy '{settings.provider_policy}'. Allowed: {sorted(allowed)}"
        )

    return settings
