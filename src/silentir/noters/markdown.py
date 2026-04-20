from __future__ import annotations

from ..types import NoteResult
from .base import BaseNoter


class MarkdownNoter(BaseNoter):
    format_name = "markdown"

    def note(self, result: NoteResult) -> str:
        return result.note_markdown.strip() + "\n"
