from __future__ import annotations

from abc import ABC, abstractmethod

from ..types import Transcript


class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        *,
        language: str | None = None,
    ) -> Transcript:
        raise NotImplementedError
