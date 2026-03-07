from __future__ import annotations

from abc import ABC, abstractmethod

from ..logging import get_logger
from ..models.base import ChatProvider
from ..types import Transcript
from .chunker import TranscriptChunker
from .prompts import PromptBuilder

logger = get_logger(__name__)


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
            logger.warning("No transcript content available for summarization.")
            return "## Overview\n\nNo transcript content available."

        logger.info("Transcript split into %d chunks for summarization.", len(chunks))
        chunk_summaries: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            logger.debug(
                "Summarizing chunk %d/%d (%.1fs - %.1fs)...", i, len(chunks), chunk.start, chunk.end
            )
            summary = provider.chat(
                model=model,
                system_prompt=self._prompts.chunk_system_prompt(language),
                user_prompt=self._prompts.chunk_user_prompt(chunk.text, chunk.start, chunk.end),
                temperature=0.2,
                max_tokens=900,
            )
            chunk_summaries.append(summary.strip())

        logger.info("Merging %d chunk summaries into final notes...", len(chunk_summaries))
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
