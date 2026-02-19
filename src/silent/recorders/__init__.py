from .base import BaseRecorder, RecorderRegistry
from .bilibili import BilibiliRecorder
from .youtube import YouTubeRecorder


def default_recorder_registry() -> RecorderRegistry:
    return RecorderRegistry([YouTubeRecorder(), BilibiliRecorder()])


__all__ = [
    "BaseRecorder",
    "RecorderRegistry",
    "YouTubeRecorder",
    "BilibiliRecorder",
    "default_recorder_registry",
]
