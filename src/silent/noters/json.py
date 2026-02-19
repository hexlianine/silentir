from __future__ import annotations

import json

from ..types import NoteResult
from .base import BaseNoter


class JsonNoter(BaseNoter):
    format_name = "json"

    def note(self, result: NoteResult) -> str:
        payload = {
            "url": result.url,
            "title": result.title,
            "language": result.language,
            "note_markdown": result.note_markdown,
            "transcript_source": result.transcript_source,
            "provider_used": result.provider_used,
            "model_used": result.model_used,
            "duration_sec": result.duration_sec,
            "warnings": result.warnings,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
