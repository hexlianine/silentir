from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# handler.py lives in skills/silentir/ — add it to the import path so tests can
# import ``_detect_agent`` from it directly.
_SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "silentir"
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

from silentir.api import generate_notes  # noqa: E402
from silentir.exceptions import ConfigurationError  # noqa: E402
from silentir.orchestrator import VideoNotesOrchestrator  # noqa: E402
from silentir.types import (  # noqa: E402
    Segment,
    Transcript,
)

# ---------------------------------------------------------------------------
# _fmt_ts helper
# ---------------------------------------------------------------------------

def test_fmt_ts_zero() -> None:
    assert VideoNotesOrchestrator._fmt_ts(0) == "00:00:00"


def test_fmt_ts_basic() -> None:
    # 1h 2m 3s
    result = VideoNotesOrchestrator._fmt_ts(3723)
    assert result == "01:02:03"


def test_fmt_ts_seconds_only() -> None:
    assert VideoNotesOrchestrator._fmt_ts(59) == "00:00:59"
    assert VideoNotesOrchestrator._fmt_ts(61) == "00:01:01"


def test_fmt_ts_large_value() -> None:
    # 10h
    assert VideoNotesOrchestrator._fmt_ts(36000) == "10:00:00"


# ---------------------------------------------------------------------------
# orchestrator.generate(transcript_only=True)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_transcript() -> Transcript:
    return Transcript(
        language="en",
        source="subtitle",
        segments=[
            Segment(start=0.0, end=5.0, text="Hello and welcome"),
            Segment(start=5.5, end=12.0, text="This is a test video"),
            Segment(start=12.5, end=20.0, text="Today we will discuss important topics"),
        ],
    )


def _make_orchestrator(transcript: Transcript) -> VideoNotesOrchestrator:
    """Build a VideoNotesOrchestrator whose recorder returns *transcript*."""
    mock_recorder = MagicMock()
    mock_recorder.platform = "youtube"
    mock_recorder.record.return_value = (
        MagicMock(
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            duration_sec=120,
        ),
        transcript,
        [],
    )
    registry = MagicMock()
    registry.match.return_value = mock_recorder

    return VideoNotesOrchestrator(
        recorder_registry=registry,
        transcriber=MagicMock(),  # never called when transcript is not None
    )


def test_transcript_only_returns_formatted_text(mock_transcript: Transcript) -> None:
    orch = _make_orchestrator(mock_transcript)
    result = orch.generate(
        url="https://youtube.com/watch?v=test",
        language=None,
        output_format="markdown",
        provider_policy="local_first",
        local_model=None,
        online_model=None,
        ollama_host="http://localhost:11434",
        openai_base_url="https://api.openai.com/v1",
        openai_api_key=None,
        include_timestamps="section",
        write_path=None,
        cookies_path=None,
        transcript_only=True,
    )
    assert result.note_markdown == (
        "[00:00:00] Hello and welcome\n"
        "[00:00:05] This is a test video\n"
        "[00:00:12] Today we will discuss important topics"
    )
    assert result.provider_used == ""
    assert result.model_used == ""


def test_transcript_only_skips_model_validation(mock_transcript: Transcript) -> None:
    """transcript_only=True should not require local_model or online_model."""
    orch = _make_orchestrator(mock_transcript)
    # Should not raise ConfigurationError
    orch.generate(
        url="https://youtube.com/watch?v=test",
        language=None,
        output_format="markdown",
        provider_policy="local_first",
        local_model=None,
        online_model=None,
        ollama_host="http://localhost:11434",
        openai_base_url="https://api.openai.com/v1",
        openai_api_key=None,
        include_timestamps="section",
        write_path=None,
        cookies_path=None,
        transcript_only=True,
    )


# ---------------------------------------------------------------------------
# api.generate_notes(transcript_only=True)
# ---------------------------------------------------------------------------

@patch("silentir.api.VideoNotesOrchestrator")
def test_api_transcript_only_no_model_required(mock_orch: MagicMock) -> None:
    """generate_notes(transcript_only=True) must not require a model."""
    # Should not raise ConfigurationError
    generate_notes(
        "https://youtube.com/watch?v=test",
        transcript_only=True,
        local_model=None,
        online_model=None,
    )
    mock_orch.return_value.generate.assert_called_once()
    kwargs = mock_orch.return_value.generate.call_args.kwargs
    assert kwargs["transcript_only"] is True


@patch("silentir.api.VideoNotesOrchestrator")
def test_api_transcript_only_passes_flag(mock_orch: MagicMock) -> None:
    """The transcript_only flag must reach orchestrator.generate()."""
    generate_notes(
        "https://youtube.com/watch?v=test",
        local_model="qwen2.5:7b-instruct",
        transcript_only=True,
    )
    mock_orch.return_value.generate.assert_called_once()
    kwargs = mock_orch.return_value.generate.call_args.kwargs
    assert kwargs["transcript_only"] is True


def test_api_requires_model_when_not_transcript_only() -> None:
    """Without transcript_only, a model is still required."""
    with pytest.raises(ConfigurationError, match="At least one model must be configured"):
        generate_notes(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            local_model=None,
            online_model=None,
            transcript_only=False,
        )


# ---------------------------------------------------------------------------
# CLI --transcript-only flag parsing
# ---------------------------------------------------------------------------

def test_cli_transcript_only_flag() -> None:
    """--transcript-only must produce transcript_only=True in parsed args."""
    from silentir.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["https://youtube.com/watch?v=test", "--transcript-only"])
    assert args.transcript_only is True


def test_cli_without_transcript_only_flag() -> None:
    """Without --transcript-only, transcript_only must be False."""
    from silentir.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["https://youtube.com/watch?v=test"])
    assert args.transcript_only is False


# ---------------------------------------------------------------------------
# handler._detect_agent()
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_env_vars() -> None:
    """Remove agent-related env vars before each test to prevent interference."""
    for key in list(os.environ):
        if key == "CLAUDECODE" or key.startswith("CODEX_") or key == "OPENCODE":
            del os.environ[key]
    # Re-apply after the test
    yield


def test_detect_agent_none() -> None:
    from handler import _detect_agent  # type: ignore[import-untyped]  # noqa: PLC0415

    assert _detect_agent() is None


def test_detect_agent_claude_code() -> None:
    from handler import _detect_agent  # noqa: PLC0415

    os.environ["CLAUDECODE"] = "1"
    assert _detect_agent() == "claude_code"


def test_detect_agent_codex() -> None:
    from handler import _detect_agent  # noqa: PLC0415

    os.environ["CODEX_THREAD_ID"] = "abc123"
    assert _detect_agent() == "codex"


def test_detect_agent_opencode() -> None:
    from handler import _detect_agent  # noqa: PLC0415

    os.environ["OPENCODE"] = "1"
    assert _detect_agent() == "opencode"


def test_detect_agent_order_claude_code_takes_precedence() -> None:
    """CLAUDECODE must be checked first; if both CLAUDECODE and CODEX_* are
    set, ``claude_code`` is returned."""
    from handler import _detect_agent  # noqa: PLC0415

    os.environ["CLAUDECODE"] = "1"
    os.environ["CODEX_THREAD_ID"] = "abc123"
    assert _detect_agent() == "claude_code"
