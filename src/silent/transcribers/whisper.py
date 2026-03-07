from __future__ import annotations

from ..exceptions import TranscriptExtractionError
from ..logging import get_logger
from ..types import Segment, Transcript
from .base import BaseTranscriber

logger = get_logger(__name__)


class WhisperASRTranscriber(BaseTranscriber):
    def __init__(self, model_size: str = "base") -> None:
        self._model_size = model_size

    def transcribe(
        self,
        audio_path: str,
        *,
        language: str | None = None,
    ) -> Transcript:
        try:
            logger.debug("Attempting transcription with faster-whisper...")
            return self._transcribe_faster_whisper(audio_path, language=language)
        except Exception as faster_exc:
            logger.debug("faster-whisper failed: %s. Falling back to openai-whisper...", faster_exc)
            try:
                return self._transcribe_openai_whisper(audio_path, language=language)
            except Exception as whisper_exc:
                logger.error("All Whisper backends failed.")
                raise TranscriptExtractionError(
                    "ASR transcription failed. Install 'faster-whisper' or 'openai-whisper', "
                    "or provide subtitles. "
                    f"faster-whisper error: {faster_exc}; whisper error: {whisper_exc}"
                ) from whisper_exc

    def _transcribe_faster_whisper(self, audio_path: str, *, language: str | None) -> Transcript:
        from faster_whisper import WhisperModel

        model = WhisperModel(self._model_size, device="auto", compute_type="int8")
        segments_iter, info = model.transcribe(
            audio_path,
            language=language if language not in {None, "auto"} else None,
        )

        segments: list[Segment] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if text:
                segments.append(Segment(start=float(seg.start), end=float(seg.end), text=text))

        detected = getattr(info, "language", None) or language or "unknown"
        logger.info("faster-whisper transcription complete. Detected language: %s", detected)
        return Transcript(language=detected, source="asr", segments=segments)

    def _transcribe_openai_whisper(self, audio_path: str, *, language: str | None) -> Transcript:
        import whisper

        model = whisper.load_model(self._model_size)
        kwargs: dict[str, str] = {}
        if language and language != "auto":
            kwargs["language"] = language
        result = model.transcribe(audio_path, **kwargs)

        segments: list[Segment] = []
        for seg in result.get("segments", []):
            text = (seg.get("text") or "").strip()
            if text:
                segments.append(
                    Segment(
                        start=float(seg.get("start", 0.0)),
                        end=float(seg.get("end", 0.0)),
                        text=text,
                    )
                )

        detected = result.get("language") or language or "unknown"
        logger.info("openai-whisper transcription complete. Detected language: %s", detected)
        return Transcript(language=detected, source="asr", segments=segments)
