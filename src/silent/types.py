from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Transcript:
    language: str
    source: Literal["subtitle", "asr"]
    segments: list[Segment]


@dataclass
class VideoMetadata:
    url: str
    title: str
    duration_sec: int | None
    platform: Literal["youtube", "bilibili"]


@dataclass
class NoteResult:
    url: str
    title: str
    language: str
    note_markdown: str
    transcript_source: str
    provider_used: str
    model_used: str
    duration_sec: int | None
    warnings: list[str] = field(default_factory=list)
