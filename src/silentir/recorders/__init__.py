from .base import BaseRecorder, RecorderRegistry
from .bilibili import BilibiliRecorder
from .file import FileRecorder
from .youtube import YouTubeRecorder


def default_recorder_registry() -> RecorderRegistry:
    return RecorderRegistry([YouTubeRecorder(), BilibiliRecorder(), FileRecorder()])


__all__ = [
    "BaseRecorder",
    "RecorderRegistry",
    "YouTubeRecorder",
    "BilibiliRecorder",
    "FileRecorder",
    "default_recorder_registry",
]
