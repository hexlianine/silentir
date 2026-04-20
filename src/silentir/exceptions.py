class VideoNotesError(Exception):
    """Base exception for the package."""


class UnsupportedURLError(VideoNotesError):
    """Raised when the URL platform is unsupported."""


class TranscriptExtractionError(VideoNotesError):
    """Raised when subtitles and ASR both fail."""


class ModelInferenceError(VideoNotesError):
    """Raised when all model providers fail."""


class ConfigurationError(VideoNotesError):
    """Raised when configuration values are invalid."""
