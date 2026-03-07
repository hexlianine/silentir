from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from ..types import Transcript, VideoMetadata
from .base import BaseRecorder

_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".webm",
    ".avi",
    ".mov",
    ".flv",
    ".wmv",
    ".m4v",
    ".ts",
    ".mpg",
    ".mpeg",
    ".3gp",
}


class FileRecorder(BaseRecorder):
    """Recorder for local video/audio files.

    Skips subtitle extraction -- the orchestrator will fall through to
    ASR (Whisper) transcription automatically.
    """

    platform = "local"

    def supports(self, url: str) -> bool:
        if url.startswith(("http://", "https://")):
            return False
        path = Path(url)
        if path.is_file():
            return True
        return path.suffix.lower() in _VIDEO_EXTENSIONS

    def record(
        self,
        url: str,
        *,
        language: str | None = None,
        cookies_path: str | None = None,
    ) -> tuple[VideoMetadata, Transcript | None, list[str]]:
        path = Path(url).resolve()
        metadata = VideoMetadata(
            url=str(path),
            title=path.stem,
            duration_sec=None,
            platform=self.platform,
        )
        warnings: list[str] = ["Local file -- no subtitles; ASR fallback will be used."]
        return metadata, None, warnings

    def download_audio(
        self,
        url: str,
        *,
        cookies_path: str | None = None,
    ) -> tuple[str, tempfile.TemporaryDirectory[str]]:
        path = Path(url).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Local file not found: {path}")

        temp_dir = tempfile.TemporaryDirectory()
        dest = os.path.join(temp_dir.name, path.name)
        # Symlink to avoid copying large files; fall back to copy.
        try:
            os.symlink(str(path), dest)
        except OSError:
            shutil.copy2(str(path), dest)
        return dest, temp_dir
