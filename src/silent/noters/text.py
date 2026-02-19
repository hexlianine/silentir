from __future__ import annotations

import re

from ..types import NoteResult
from .base import BaseNoter


_HEADER_RE = re.compile(r"^#{1,6}\s*", flags=re.MULTILINE)


class TextNoter(BaseNoter):
    format_name = "text"

    def note(self, result: NoteResult) -> str:
        plain = _HEADER_RE.sub("", result.note_markdown)
        plain = plain.replace("**", "")
        return plain.strip() + "\n"
