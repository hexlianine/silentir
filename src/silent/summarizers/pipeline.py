from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.base import ChatProvider
from ..types import Transcript
from .chunker import TranscriptChunker
from .prompts import PromptBuilder


class BaseSummarizer(ABC):
    @abstractmethod
    def summarize(
        self,
        transcript: Transcript,
        *,
        provider: ChatProvider,
        model: str,
        language: str,
        include_timestamps: str,
    ) -> str:
        raise NotImplementedError


class HierarchicalSummarizer(BaseSummarizer):
    def __init__(
        self,
        *,
        chunker: TranscriptChunker | None = None,
        prompts: PromptBuilder | None = None,
    ) -> None:
        self._chunker = chunker or TranscriptChunker()
        self._prompts = prompts or PromptBuilder()

    def summarize(
        self,
        transcript: Transcript,
        *,
        provider: ChatProvider,
        model: str,
        language: str,
        include_timestamps: str = "section",
    ) -> str:
        chunks = self._chunker.chunk(transcript)
        if not chunks:
            return "## Overview\n\nNo transcript content available."

        chunk_summaries: list[str] = []
        for chunk in chunks:
            summary = provider.chat(
                model=model,
                system_prompt=self._prompts.chunk_system_prompt(language),
                user_prompt=self._prompts.chunk_user_prompt(chunk.text, chunk.start, chunk.end),
                temperature=0.2,
                max_tokens=900,
            )
            chunk_summaries.append(summary.strip())

        merged = provider.chat(
            model=model,
            system_prompt=self._prompts.merge_system_prompt(
                language, include_timestamps=include_timestamps
            ),
            user_prompt=self._prompts.merge_user_prompt(chunk_summaries),
            temperature=0.1,
            max_tokens=1500,
        )
        return merged.strip()
