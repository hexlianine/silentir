from .base import BaseRecorder, RecorderRegistry
from .bilibili import BilibiliRecorder
from .file import FileRecorder
from .youtube import YouTubeRecorder


def default_recorder_registry(*, bilibili_backend: str = "auto") -> RecorderRegistry:
    return RecorderRegistry(
        [
            YouTubeRecorder(),
            BilibiliRecorder(backend=bilibili_backend),
            FileRecorder(),
        ]
    )


__all__ = [
    "BaseRecorder",
    "RecorderRegistry",
    "YouTubeRecorder",
    "BilibiliRecorder",
    "FileRecorder",
    "default_recorder_registry",
]
