from __future__ import annotations

from abc import ABC, abstractmethod

from ..types import NoteResult


class BaseNoter(ABC):
    format_name: str

    @abstractmethod
    def note(self, result: NoteResult) -> str:
        raise NotImplementedError


class NoterRegistry:
    def __init__(self, noters: list[BaseNoter]) -> None:
        self._noters = {noter.format_name: noter for noter in noters}

    def note(self, format_name: str, result: NoteResult) -> str:
        return self.get(format_name).note(result)

    def get(self, format_name: str) -> BaseNoter:
        noter = self._noters.get(format_name)
        if noter is None:
            raise ValueError(f"Unsupported output format: {format_name}")
        return noter
