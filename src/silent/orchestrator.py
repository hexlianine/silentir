from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import OutputFormat, TimestampMode, load_settings
from .exceptions import ModelInferenceError
from .models.base import ChatProvider, ProviderUnavailable
from .models.ollama_provider import OllamaProvider
from .models.openai_compatible_provider import OpenAICompatibleProvider
from .noters import NoterRegistry, default_noter_registry
from .recorders import RecorderRegistry, default_recorder_registry
from .summarizers import BaseSummarizer, HierarchicalSummarizer
from .transcribers import BaseTranscriber, WhisperASRTranscriber
from .types import NoteResult


@dataclass
class ProviderCandidate:
    provider: ChatProvider
    model: str


def provider_order(policy: str) -> list[str]:
    if policy == "local_first":
        return ["local", "online"]
    if policy == "online_first":
        return ["online", "local"]
    if policy == "local_only":
        return ["local"]
    if policy == "online_only":
        return ["online"]
    raise ValueError(f"Unknown provider policy: {policy}")


class VideoNotesOrchestrator:
    def __init__(
        self,
        *,
        recorder_registry: RecorderRegistry | None = None,
        transcriber: BaseTranscriber | None = None,
        summarizer: BaseSummarizer | None = None,
        noter_registry: NoterRegistry | None = None,
    ) -> None:
        self._recorder_registry = recorder_registry or default_recorder_registry()
        self._transcriber = transcriber or WhisperASRTranscriber()
        self._summarizer = summarizer or HierarchicalSummarizer()
        self._noter_registry = noter_registry or default_noter_registry()

    def generate(
        self,
        *,
        url: str,
        language: str | None,
        output_format: OutputFormat,
        provider_policy: str,
        local_model: str,
        online_model: str,
        include_timestamps: TimestampMode,
        write_path: str | None,
        cookies_path: str | None,
    ) -> NoteResult:
        settings = load_settings(
            provider_policy=provider_policy,
            local_model=local_model,
            online_model=online_model,
        )

        recorder = self._recorder_registry.match(url)
        metadata, transcript, warnings = recorder.record(
            url,
            language=language,
            cookies_path=cookies_path,
        )

        if transcript is None:
            audio_path, temp_dir = recorder.download_audio(url, cookies_path=cookies_path)
            try:
                transcript = self._transcriber.transcribe(audio_path, language=language)
            finally:
                temp_dir.cleanup()

        effective_language = transcript.language if language in {None, "auto"} else language

        providers = self._provider_candidates(
            policy=settings.provider_policy,
            local_model=settings.local_model,
            online_model=settings.online_model,
            ollama_host=settings.ollama_host,
            openai_base_url=settings.openai_base_url,
            openai_api_key=settings.openai_api_key,
        )

        last_err: Exception | None = None
        provider_used = ""
        model_used = ""
        note_markdown = ""

        for candidate in providers:
            try:
                note_markdown = self._summarizer.summarize(
                    transcript,
                    provider=candidate.provider,
                    model=candidate.model,
                    language=effective_language,
                    include_timestamps=include_timestamps,
                )
                provider_used = candidate.provider.name
                model_used = candidate.model
                break
            except ProviderUnavailable as exc:
                warnings.append(f"Provider '{candidate.provider.name}' failed: {exc}")
                last_err = exc

        if not note_markdown:
            raise ModelInferenceError(
                f"All provider attempts failed. Last error: {last_err}"
            ) from last_err

        result = NoteResult(
            url=metadata.url,
            title=metadata.title,
            language=effective_language,
            note_markdown=note_markdown,
            transcript_source=transcript.source,
            provider_used=provider_used,
            model_used=model_used,
            duration_sec=metadata.duration_sec,
            warnings=warnings,
        )

        if write_path:
            rendered = self._noter_registry.note(output_format, result)
            Path(write_path).write_text(rendered, encoding="utf-8")

        return result

    def render(self, output_format: OutputFormat, result: NoteResult) -> str:
        return self._noter_registry.note(output_format, result)

    @staticmethod
    def _provider_candidates(
        *,
        policy: str,
        local_model: str,
        online_model: str,
        ollama_host: str,
        openai_base_url: str,
        openai_api_key: str | None,
    ) -> list[ProviderCandidate]:
        order = provider_order(policy)
        candidates: list[ProviderCandidate] = []
        for item in order:
            if item == "local":
                candidates.append(
                    ProviderCandidate(
                        provider=OllamaProvider(host=ollama_host),
                        model=local_model,
                    )
                )
            else:
                candidates.append(
                    ProviderCandidate(
                        provider=OpenAICompatibleProvider(
                            base_url=openai_base_url,
                            api_key=openai_api_key,
                        ),
                        model=online_model,
                    )
                )
        return candidates
