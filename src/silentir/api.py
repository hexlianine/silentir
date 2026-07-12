from __future__ import annotations

from silentir.logging import get_logger

from .exceptions import ConfigurationError
from .orchestrator import VideoNotesOrchestrator
from .types import NoteResult, OutputFormat, ProviderPolicy, TimestampMode


def generate_notes(
    url: str,
    *,
    language: str | None = None,
    output_format: OutputFormat = "markdown",
    provider_policy: ProviderPolicy = "local_first",
    local_model: str | None = None,
    online_model: str | None = None,
    ollama_host: str = "http://localhost:11434",
    openai_base_url: str = "https://api.openai.com/v1",
    openai_api_key: str | None = None,
    include_timestamps: TimestampMode = "section",
    write_path: str | None = None,
    cookies_path: str | None = None,
    bilibili_backend: str = "auto",
    transcript_only: bool = False,
) -> NoteResult:
    logger = get_logger()
    logger.debug(
        "Generating notes with parameters: "
        "url=%r, language=%r, output_format=%r, provider_policy=%r, local_model=%r, "
        "online_model=%r, ollama_host=%r, openai_base_url=%r, include_timestamps=%r, "
        "write_path=%r, cookies_path=%r, bilibili_backend=%r, transcript_only=%r",
        url,
        language,
        output_format,
        provider_policy,
        local_model,
        online_model,
        ollama_host,
        openai_base_url,
        include_timestamps,
        write_path,
        cookies_path,
        bilibili_backend,
        transcript_only,
    )

    if not transcript_only and local_model is None and online_model is None:
        raise ConfigurationError(
            "At least one model must be configured: local_model or online_model."
        )

    orchestrator = VideoNotesOrchestrator(bilibili_backend=bilibili_backend)
    return orchestrator.generate(
        url=url,
        language=language,
        output_format=output_format,
        provider_policy=provider_policy,
        local_model=local_model,
        online_model=online_model,
        ollama_host=ollama_host,
        openai_base_url=openai_base_url,
        openai_api_key=openai_api_key,
        include_timestamps=include_timestamps,
        write_path=write_path,
        cookies_path=cookies_path,
        transcript_only=transcript_only,
    )
