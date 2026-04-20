from __future__ import annotations

from .base import BaseRecorder, normalized_domain


class YouTubeRecorder(BaseRecorder):
    platform = "youtube"

    def supports(self, url: str) -> bool:
        host = normalized_domain(url)
        return host in {"youtube.com", "youtu.be", "m.youtube.com"}
