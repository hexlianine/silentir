from __future__ import annotations

from .base import BaseRecorder, normalized_domain


class BilibiliRecorder(BaseRecorder):
    platform = "bilibili"

    def supports(self, url: str) -> bool:
        host = normalized_domain(url)
        return host.endswith("bilibili.com") or host.endswith("b23.tv")
