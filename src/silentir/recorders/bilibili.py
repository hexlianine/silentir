from __future__ import annotations

import json
import shutil
import subprocess

from ..exceptions import TranscriptExtractionError
from ..logging import get_logger
from ..types import Segment, Transcript, VideoMetadata
from .base import BaseRecorder, normalized_domain

logger = get_logger(__name__)

# Hard timeout for a single `bili video` invocation. bilibili-cli may spend time
# probing browser cookies before falling back to saved credentials, so give it room.
_BILI_TIMEOUT = 60

# Bilibili subtitles are predominantly Chinese; bilibili-cli prefers `zh` when
# fetching. Used as the transcript language because the CLI does not expose the
# resolved subtitle language in its normalized payload.
_DEFAULT_BILI_LANGUAGE = "zh"


class _BiliUnavailable(Exception):
    """Internal signal: the bilibili-cli path failed and should fall back to yt-dlp."""


class BilibiliRecorder(BaseRecorder):
    platform = "bilibili"

    def __init__(self, *, backend: str = "auto") -> None:
        if backend not in {"auto", "bili", "ytdlp"}:
            raise ValueError(f"Unknown bilibili backend: {backend!r}. Allowed: auto, bili, ytdlp")
        self._backend = backend

    def supports(self, url: str) -> bool:
        host = normalized_domain(url)
        return host.endswith("bilibili.com") or host.endswith("b23.tv")

    def record(
        self,
        url: str,
        *,
        language: str | None = None,
        cookies_path: str | None = None,
    ) -> tuple[VideoMetadata, Transcript | None, list[str]]:
        warnings: list[str] = []

        if self._backend in {"auto", "bili"}:
            if self._bili_available():
                try:
                    metadata, transcript = self._record_via_bili(url)
                    logger.info("Extracted Bilibili subtitles via bilibili-cli")
                    if transcript is None:
                        warnings.append(
                            "bilibili-cli reported no subtitles; ASR fallback will be used."
                        )
                    return metadata, transcript, warnings
                except _BiliUnavailable as exc:
                    if self._backend == "bili":
                        # Fallback disabled by explicit configuration.
                        raise TranscriptExtractionError(
                            f"bilibili-cli backend failed and fallback is disabled: {exc}"
                        ) from exc
                    logger.warning("bilibili-cli failed, falling back to yt-dlp: %s", exc)
                    warnings.append(f"bilibili-cli unavailable ({exc}); falling back to yt-dlp.")
            elif self._backend == "bili":
                raise TranscriptExtractionError(
                    "bilibili-cli backend requested but the 'bili' command was not found. "
                    "Install it with: uv tool install bilibili-cli"
                )

        # yt-dlp fallback: merge any warnings accumulated above (e.g. bili failure).
        metadata, transcript, fallback_warnings = super().record(
            url, language=language, cookies_path=cookies_path
        )
        return metadata, transcript, warnings + fallback_warnings

    @staticmethod
    def _bili_available() -> bool:
        return shutil.which("bili") is not None

    def _record_via_bili(self, url: str) -> tuple[VideoMetadata, Transcript | None]:
        cmd = ["bili", "video", url, "--subtitle-timeline", "--json"]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_BILI_TIMEOUT,
                check=False,
            )
        except FileNotFoundError as exc:
            raise _BiliUnavailable("'bili' command not found") from exc
        except subprocess.TimeoutExpired as exc:
            raise _BiliUnavailable(f"'bili' timed out after {_BILI_TIMEOUT}s") from exc

        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "").strip().splitlines()
            tail = stderr_tail[-1] if stderr_tail else ""
            raise _BiliUnavailable(f"'bili' exited with code {proc.returncode}: {tail}".strip())

        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise _BiliUnavailable(f"'bili' returned non-JSON output: {exc}") from exc

        if not payload.get("ok"):
            err = payload.get("error") or {}
            code = err.get("code", "unknown")
            message = err.get("message", "")
            raise _BiliUnavailable(f"'bili' reported error: {code} - {message}".strip())

        data = payload.get("data") or {}
        metadata = self._metadata_from_payload(url, data.get("video") or {})
        transcript = self._transcript_from_payload(data.get("subtitle") or {})
        return metadata, transcript

    @staticmethod
    def _metadata_from_payload(url: str, video: dict) -> VideoMetadata:
        duration_sec = video.get("duration_seconds")
        if not isinstance(duration_sec, int):
            duration_sec = None
        return VideoMetadata(
            url=url,
            title=video.get("title") or "Untitled",
            duration_sec=duration_sec,
            platform="bilibili",
        )

    @staticmethod
    def _transcript_from_payload(subtitle: dict) -> Transcript | None:
        if not subtitle.get("available"):
            return None

        segments: list[Segment] = []
        for item in subtitle.get("items") or []:
            if not isinstance(item, dict):
                continue
            text = (item.get("content") or "").strip()
            if not text:
                continue
            try:
                start = float(item.get("from", 0.0) or 0.0)
                end = float(item.get("to", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            segments.append(Segment(start=start, end=end, text=text))

        if not segments:
            return None

        return Transcript(language=_DEFAULT_BILI_LANGUAGE, source="subtitle", segments=segments)
