from __future__ import annotations

import re

from ..types import Segment

_TIMESTAMP_RE = re.compile(
    r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})\.(?P<ms>\d{3})\s+-->\s+(?P<h2>\d{2}):(?P<m2>\d{2}):(?P<s2>\d{2})\.(?P<ms2>\d{3})"
)


def _to_sec(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt_text(vtt_text: str) -> list[Segment]:
    lines = vtt_text.splitlines()
    segments: list[Segment] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = _TIMESTAMP_RE.search(line)
        if not match:
            i += 1
            continue

        start = _to_sec(match.group("h"), match.group("m"), match.group("s"), match.group("ms"))
        end = _to_sec(match.group("h2"), match.group("m2"), match.group("s2"), match.group("ms2"))

        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i].strip())
            i += 1

        text = " ".join(text_lines).strip()
        if text:
            segments.append(Segment(start=start, end=end, text=text))
    return segments
