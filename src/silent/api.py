from __future__ import annotations

from .config import OutputFormat, TimestampMode
from .orchestrator import VideoNotesOrchestrator
from .types import NoteResult


def generate_notes(
    url: str,
    *,
    language: str | None = None,
    output_format: OutputFormat = "markdown",
    provider_policy: str = "local_first",
    local_model: str = "qwen2.5:7b-instruct",
    online_model: str = "gpt-4.1-mini",
    include_timestamps: TimestampMode = "section",
    write_path: str | None = None,
    cookies_path: str | None = None,
) -> NoteResult:
    orchestrator = VideoNotesOrchestrator()
    return orchestrator.generate(
        url=url,
        language=language,
        output_format=output_format,
        provider_policy=provider_policy,
        local_model=local_model,
        online_model=online_model,
        include_timestamps=include_timestamps,
        write_path=write_path,
        cookies_path=cookies_path,
    )
