from __future__ import annotations

import os
import tempfile
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from urllib.request import urlopen

from ..exceptions import TranscriptExtractionError, UnsupportedURLError
from ..logging import get_logger
from ..transcribers.subtitles import parse_vtt_text
from ..types import Segment, Transcript, VideoMetadata

logger = get_logger(__name__)


class BaseRecorder(ABC):
    platform: str

    @abstractmethod
    def supports(self, url: str) -> bool:
        raise NotImplementedError

    def record(
        self,
        url: str,
        *,
        language: str | None = None,
        cookies_path: str | None = None,
    ) -> tuple[VideoMetadata, Transcript | None, list[str]]:
        info = self._fetch_info(url, cookies_path=cookies_path)
        metadata = VideoMetadata(
            url=url,
            title=info.get("title") or "Untitled",
            duration_sec=info.get("duration"),
            platform=self.platform,  # type: ignore[arg-type]
        )
        logger.info("Extracted metadata for '%s' [%s]", metadata.title, self.platform)
        warnings: list[str] = []

        transcript = self._record_subtitle_transcript(info, language=language)
        if transcript is None:
            warnings.append("No subtitles found; ASR fallback will be used.")
        return metadata, transcript, warnings

    def download_audio(
        self,
        url: str,
        *,
        cookies_path: str | None = None,
    ) -> tuple[str, tempfile.TemporaryDirectory[str]]:
        try:
            import yt_dlp
        except Exception as exc:  # pragma: no cover
            raise TranscriptExtractionError(
                "yt-dlp is required for audio extraction. Install dependency 'yt-dlp'."
            ) from exc

        temp_dir = tempfile.TemporaryDirectory()
        outtmpl = os.path.join(temp_dir.name, "audio.%(ext)s")
        opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "outtmpl": outtmpl,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                }
            },
        }
        if cookies_path:
            opts["cookiefile"] = cookies_path

        try:
            logger.info("Downloading audio from %s...", url)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as exc:
            temp_dir.cleanup()
            logger.error("Failed to download audio: %s", exc)
            raise TranscriptExtractionError(f"Failed to download audio: {exc}") from exc

        files = [f for f in os.listdir(temp_dir.name) if f.startswith("audio.")]
        if not files:
            temp_dir.cleanup()
            raise TranscriptExtractionError("Audio download succeeded but output file is missing.")
        return os.path.join(temp_dir.name, files[0]), temp_dir

    def _fetch_info(self, url: str, *, cookies_path: str | None = None) -> dict:
        try:
            import yt_dlp
        except Exception as exc:  # pragma: no cover
            raise TranscriptExtractionError(
                "yt-dlp is required for URL extraction. Install dependency 'yt-dlp'."
            ) from exc

        opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                }
            },
        }
        if cookies_path:
            opts["cookiefile"] = cookies_path

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as exc:
            raise TranscriptExtractionError(f"Failed to extract metadata/subtitles: {exc}") from exc

    def _record_subtitle_transcript(
        self, info: dict, *, language: str | None = None
    ) -> Transcript | None:
        preferred: list[str] = []
        if language and language != "auto":
            preferred.append(language)

        subtitles = info.get("subtitles") or {}
        automatic = info.get("automatic_captions") or {}
        candidates = self._subtitle_candidates(subtitles, preferred) + self._subtitle_candidates(
            automatic, preferred
        )
        if not candidates:
            return None

        for lang, entry in candidates:
            subtitle_url = entry.get("url")
            ext = entry.get("ext", "")
            if not subtitle_url:
                continue
            try:
                segments = self._download_and_parse_subtitle(subtitle_url, ext)
            except Exception:
                continue
            if segments:
                logger.debug("Selected subtitles: language='%s', ext='%s'", lang, ext)
                return Transcript(language=lang, source="subtitle", segments=segments)

        logger.debug("No suitable subtitles found in metadata.")
        return None

    @staticmethod
    def _subtitle_candidates(sub_map: dict, preferred: list[str]) -> list[tuple[str, dict]]:
        logger.debug("Finding subtitle candidates. Preferred languages: %s", preferred)
        ordered_langs: list[str] = []
        for lang in preferred:
            if lang in sub_map:
                ordered_langs.append(lang)
        for lang in sub_map.keys():
            if lang not in ordered_langs:
                ordered_langs.append(lang)

        candidates: list[tuple[str, dict]] = []
        for lang in ordered_langs:
            formats = sub_map.get(lang) or []
            formats = sorted(formats, key=lambda item: 0 if item.get("ext") == "vtt" else 1)
            for item in formats:
                if item.get("url"):
                    candidates.append((lang, item))
        return candidates

    @staticmethod
    def _download_and_parse_subtitle(url: str, ext: str) -> list[Segment]:
        with urlopen(url, timeout=20) as resp:
            payload = resp.read()
        text = payload.decode("utf-8", errors="replace")

        if ext == "vtt" or "WEBVTT" in text[:100]:
            return parse_vtt_text(text)

        segments: list[Segment] = []
        for idx, raw in enumerate(line.strip() for line in text.splitlines() if line.strip()):
            segments.append(Segment(start=float(idx), end=float(idx + 1), text=raw))
        return segments


class RecorderRegistry:
    def __init__(self, recorders: list[BaseRecorder]) -> None:
        self._recorders = recorders

    def match(self, url: str) -> BaseRecorder:
        for recorder in self._recorders:
            if recorder.supports(url):
                return recorder
        raise UnsupportedURLError(
            "Unsupported source. Supports YouTube URLs, Bilibili URLs, or local video file paths."
        )


def normalized_domain(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host
