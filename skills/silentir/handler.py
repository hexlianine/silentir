#!/usr/bin/env python3
"""Skill handler for `silentir` — delegates to the PyPI release.

Runs the published `silentir` console script via `uvx`, so this handler
works in any project without needing a local source checkout. The
`[asr]` extra is pulled in so Whisper-based transcription is available
for local files and for remote videos that don't expose subtitles.

When silentir fails, this handler classifies the error (configuration,
unsupported source, transcript extraction, model inference, ...) and
emits a structured remediation block on stderr so the calling agent can
turn it into a precise follow-up question for the user.

Env vars used as defaults when the matching CLI flag is omitted:
  LOCAL_MODEL, ONLINE_MODEL, OPENAI_BASE_URL, OPENAI_API_KEY
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

SILENTIR_SPEC = "silentir[asr]"

# Exit codes mirror the upstream CLI:
#   src/silentir/cli.py raises with sys.exit(2|3|4) for the four typed
#   exceptions (UnsupportedURLError, ConfigurationError, TranscriptExtractionError,
#   ModelInferenceError).
EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_CONFIG_OR_UNSUPPORTED = 2
EXIT_TRANSCRIPT = 3
EXIT_MODEL = 4
EXIT_MISSING_UVX = 127


@dataclass
class FailureReport:
    """Structured failure signal the calling agent can act on."""

    category: str
    exit_code: int
    detail: str
    ask_user: list[str] = field(default_factory=list)
    remediations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Silentir Skill Handler")
    parser.add_argument(
        "source",
        help="YouTube/Bilibili URL or local video/audio file path",
    )
    parser.add_argument("--language", default="auto", help="Language for notes")
    parser.add_argument("--local-model", help="Local Ollama model name")
    parser.add_argument("--online-model", help="Online OpenAI-compatible model name")
    parser.add_argument(
        "--provider-policy",
        default="local_first",
        choices=["local_first", "online_first", "local_only", "online_only"],
    )
    parser.add_argument(
        "--ollama-host",
        default="http://localhost:11434",
        help="Ollama host URL",
    )
    parser.add_argument(
        "--include-timestamps",
        default="section",
        choices=["section", "point", "none"],
    )
    parser.add_argument(
        "--output-format",
        default="markdown",
        choices=["markdown", "text", "json"],
    )
    parser.add_argument("--out", help="Optional output file path")
    parser.add_argument("--cookies", help="Optional cookies.txt path")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--silentir-version",
        default=None,
        help="Optional version pin, e.g. '0.1.1'. Defaults to the latest on PyPI.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Remediation emission
# ---------------------------------------------------------------------------

_BLOCK_OPEN = "=== silentir failed ==="
_BLOCK_CLOSE = "=== end silentir failure ==="


def emit_failure(report: FailureReport) -> None:
    """Print a labeled, easy-to-parse failure block to stderr."""
    lines: list[str] = [
        "",
        _BLOCK_OPEN,
        f"category: {report.category}",
        f"exit_code: {report.exit_code}",
        f"detail: {report.detail}",
    ]
    if report.ask_user:
        lines.append("ask_user:")
        for item in report.ask_user:
            lines.append(f"  - {item}")
    if report.remediations:
        lines.append("remediations:")
        for item in report.remediations:
            lines.append(f"  - {item}")
    lines.append(_BLOCK_CLOSE)
    lines.append("")
    sys.stderr.write("\n".join(lines))
    sys.stderr.flush()


# ---------------------------------------------------------------------------
# Preflight — fail fast before paying the uvx startup cost
# ---------------------------------------------------------------------------


def _looks_like_url(source: str) -> bool:
    return source.startswith(("http://", "https://"))


def preflight(args: argparse.Namespace) -> FailureReport | None:
    """Catch obvious user errors before invoking uvx."""

    # 1) Local-path source that doesn't exist on disk.
    if not _looks_like_url(args.source):
        if not os.path.exists(args.source):
            return FailureReport(
                category="unsupported_source",
                exit_code=EXIT_CONFIG_OR_UNSUPPORTED,
                detail=(
                    f"Source '{args.source}' is not a YouTube/Bilibili URL and no "
                    "file exists at that path."
                ),
                ask_user=[
                    "Did you mean to provide a different file path? Please paste the "
                    "absolute path to the video or audio file.",
                    "Or did you mean to provide a YouTube or Bilibili URL? If so, "
                    "please share the full URL (starting with https://).",
                ],
                remediations=[
                    "Run `ls <path>` to confirm the file exists.",
                    "Verify the URL begins with http:// or https://.",
                ],
            )

    # 2) Cookies path that doesn't exist.
    if args.cookies and not os.path.isfile(args.cookies):
        return FailureReport(
            category="unsupported_source",
            exit_code=EXIT_CONFIG_OR_UNSUPPORTED,
            detail=f"--cookies path '{args.cookies}' does not exist.",
            ask_user=["Where is the cookies.txt file located? Please share the absolute path."],
            remediations=[
                "Export cookies for the relevant site (e.g. via the 'Get cookies.txt' "
                "browser extension) and pass that file path to --cookies.",
            ],
        )

    # 3) online_only policy without any way to reach an online provider.
    if args.provider_policy == "online_only":
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENAI_BASE_URL")  # custom endpoints sometimes don't need a key
        )
        has_explicit_model = bool(args.online_model or os.getenv("ONLINE_MODEL"))
        if not api_key and not has_explicit_model:
            return FailureReport(
                category="configuration",
                exit_code=EXIT_CONFIG_OR_UNSUPPORTED,
                detail=(
                    "provider_policy='online_only' was requested but neither "
                    "OPENAI_API_KEY/OPENAI_BASE_URL nor an --online-model value was "
                    "supplied."
                ),
                ask_user=[
                    "Which online provider should be used? Please provide either an "
                    "OPENAI_API_KEY for api.openai.com, or both OPENAI_BASE_URL and "
                    "(optionally) OPENAI_API_KEY for an OpenAI-compatible endpoint.",
                    "If a local Ollama model is acceptable, would you like to switch "
                    "to provider_policy='local_first' instead?",
                ],
                remediations=[
                    "Export OPENAI_API_KEY (and OPENAI_BASE_URL if non-default) before re-running.",
                    "Pass --online-model <name> to be explicit about the target model.",
                    "Re-run with --provider-policy local_first to use the local model fallback.",
                ],
            )

    # 4) local_only policy with no local_model anywhere.
    if args.provider_policy == "local_only":
        if not args.local_model and not os.getenv("LOCAL_MODEL"):
            # The handler also defaults to qwen2.5:7b-instruct further down, so this
            # only fires if the caller explicitly disabled that default.
            return FailureReport(
                category="configuration",
                exit_code=EXIT_CONFIG_OR_UNSUPPORTED,
                detail=(
                    "provider_policy='local_only' was requested without a "
                    "--local-model or LOCAL_MODEL value."
                ),
                ask_user=[
                    "Which Ollama model should be used (e.g. 'qwen2.5:7b-instruct', "
                    "'llama3.1:8b-instruct-q4_K_M')? You can list installed models "
                    "with `ollama list`.",
                ],
                remediations=[
                    "Pass --local-model <name>, or export LOCAL_MODEL=<name>.",
                ],
            )

    return None


# ---------------------------------------------------------------------------
# Post-mortem classification — what to ask after silentir already ran
# ---------------------------------------------------------------------------


def classify(returncode: int, stderr: str, args: argparse.Namespace) -> FailureReport:
    """Turn a nonzero exit code + stderr into an actionable FailureReport."""

    detail = _extract_error_line(stderr) or stderr.strip()[:400] or "(no stderr captured)"
    lowered = stderr.lower()
    is_url = _looks_like_url(args.source)

    # Exit 2: UnsupportedURLError OR ConfigurationError. Disambiguate by message.
    if returncode == EXIT_CONFIG_OR_UNSUPPORTED:
        if "unsupported source" in lowered or "supports youtube urls" in lowered:
            return FailureReport(
                category="unsupported_source",
                exit_code=returncode,
                detail=detail,
                ask_user=[
                    "Please confirm the source string. It must be a YouTube URL "
                    "(youtube.com, youtu.be), a Bilibili URL (bilibili.com, b23.tv), "
                    "or a local file with a recognized video extension (mp4, mkv, "
                    "webm, mov, …) that exists on disk.",
                ],
                remediations=[
                    "Re-run with --verbose to see the routing decision.",
                ],
            )
        if "provider policy" in lowered or "at least one model" in lowered:
            return FailureReport(
                category="configuration",
                exit_code=returncode,
                detail=detail,
                ask_user=[
                    "Which provider should be used? Options: local_first, "
                    "online_first, local_only, online_only.",
                    "Please supply --local-model (Ollama) or --online-model "
                    "(OpenAI-compatible) so silentir has something to call.",
                ],
                remediations=[
                    "Pass --local-model <name> and/or --online-model <name>.",
                    "Export LOCAL_MODEL / ONLINE_MODEL env vars to set defaults.",
                ],
            )
        # Fallback for exit 2.
        return FailureReport(
            category="configuration",
            exit_code=returncode,
            detail=detail,
            ask_user=[
                "Something about the source or configuration was rejected. Please "
                "review the detail line above and confirm the arguments."
            ],
        )

    # Exit 3: TranscriptExtractionError.
    if returncode == EXIT_TRANSCRIPT:
        ask: list[str] = []
        remedies: list[str] = []
        if is_url:
            ask.append(
                "Is the video private, age-gated, region-locked, or members-only? "
                "If so, can you export browser cookies for that site to a "
                "cookies.txt file and re-run with --cookies <path>?"
            )
            ask.append(
                "Has the video been removed or is the URL still reachable from a "
                "browser on this network?"
            )
            remedies.append("Re-run with --cookies <path/to/cookies.txt>.")
            remedies.append("Try a different URL (e.g. an unlisted but accessible mirror).")
        else:
            ask.append(
                "Does the file contain an audio track? Some screen-recording "
                "formats are video-only. Can you confirm with `ffprobe <file>`?"
            )
            ask.append(
                "Is the file path readable by the current user? Please confirm "
                "with `ls -la <path>`."
            )
            remedies.append("Re-mux or re-encode the file to include an audio track.")
            remedies.append("Try a different source file.")
        if "asr support requires" in lowered or "ffmpeg" in lowered:
            ask.append(
                "ASR fell over while loading Whisper or ffmpeg. Is ffmpeg installed "
                "and on PATH (`which ffmpeg`)?"
            )
            remedies.append("Install ffmpeg (`brew install ffmpeg` on macOS).")
        remedies.append("Re-run with --verbose for the full extraction trace.")
        return FailureReport(
            category="transcript_extraction",
            exit_code=returncode,
            detail=detail,
            ask_user=ask,
            remediations=remedies,
        )

    # Exit 4: ModelInferenceError — provider call failed.
    if returncode == EXIT_MODEL:
        ask = []
        remedies = []
        is_ollama_problem = any(
            tok in lowered for tok in ("ollama", "11434", "connection refused", "localhost")
        )
        is_api_auth = any(
            tok in lowered
            for tok in ("401", "unauthorized", "invalid api key", "incorrect api key")
        )
        is_quota = any(
            tok in lowered for tok in ("quota", "rate limit", "429", "insufficient_quota")
        )

        if is_ollama_problem or args.provider_policy in ("local_first", "local_only"):
            ask.append(
                f"Is Ollama running at {args.ollama_host}? Try `curl {args.ollama_host}/api/tags`."
            )
            ask.append(
                "Is the requested local model installed? Run `ollama list` and "
                "confirm the model from --local-model is present."
            )
            remedies.append("Start Ollama: `ollama serve` (or open the desktop app).")
            remedies.append(
                "Pull the model first: `ollama pull "
                f"{args.local_model or os.getenv('LOCAL_MODEL') or 'qwen2.5:7b-instruct'}`."
            )
        if is_api_auth or args.provider_policy in ("online_first", "online_only"):
            ask.append(
                "Is OPENAI_API_KEY set and valid? Some providers also require "
                "OPENAI_BASE_URL — please confirm both."
            )
            remedies.append("Export a valid OPENAI_API_KEY before re-running.")
        if is_quota:
            ask.append(
                "Did the online provider report a quota/rate-limit error? Would you "
                "like to switch to a different model or to provider_policy=local_first?"
            )
            remedies.append("Pass --online-model <cheaper-or-different-model>.")
            remedies.append("Re-run with --provider-policy local_first to fall back to Ollama.")

        if not ask:
            ask.append(
                "The summarization step failed but the cause isn't obvious from the "
                "error message. Please review the detail line above and decide "
                "whether to retry with a different model or provider policy."
            )
        remedies.append("Re-run with --verbose for the full provider trace.")
        return FailureReport(
            category="model_inference",
            exit_code=returncode,
            detail=detail,
            ask_user=ask,
            remediations=remedies,
        )

    # Anything else — uvx crashed, network died, etc.
    return FailureReport(
        category="unknown",
        exit_code=returncode,
        detail=detail,
        ask_user=[
            "silentir exited with an unexpected status. Please review the stderr "
            "above and decide whether to retry, switch providers, or report this "
            "as a bug."
        ],
        remediations=[
            "Re-run with --verbose for the full trace.",
            "Check connectivity to PyPI and to the configured model providers.",
        ],
    )


def _extract_error_line(stderr: str) -> str | None:
    """Pull the first `Error: ...` line out of the upstream CLI's stderr."""
    for raw in stderr.splitlines():
        line = raw.strip()
        if line.startswith("Error:"):
            return line[len("Error:") :].strip()
    return None


# ---------------------------------------------------------------------------
# Agent context auto-detection
# ---------------------------------------------------------------------------


def _detect_agent() -> str | None:
    """Auto-detect if running inside a CLI coding agent via env vars.

    Returns the agent name (``"claude_code"``, ``"codex"``, ``"opencode"``)
    or *None* when no known agent is detected.
    """
    # Claude Code — the canonical env var set in all subprocesses.
    if os.environ.get("CLAUDECODE") == "1":
        return "claude_code"
    # OpenAI Codex CLI
    if any(k.startswith("CODEX_") for k in os.environ):
        return "codex"
    # OpenCode
    if os.environ.get("OPENCODE") is not None:
        return "opencode"
    return None


# ---------------------------------------------------------------------------
# uvx command construction
# ---------------------------------------------------------------------------


def build_uvx_cmd(args: argparse.Namespace) -> list[str]:
    spec = SILENTIR_SPEC
    if args.silentir_version:
        spec = f"silentir[asr]=={args.silentir_version}"

    local_model = args.local_model or os.getenv("LOCAL_MODEL") or "qwen2.5:7b-instruct"
    online_model = args.online_model or os.getenv("ONLINE_MODEL") or "gpt-4.1-mini"
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    cmd: list[str] = [
        "uvx",
        "--from",
        spec,
        "silentir",
        args.source,
        "--language",
        args.language,
        "--provider-policy",
        args.provider_policy,
        "--local-model",
        local_model,
        "--online-model",
        online_model,
        "--ollama-host",
        args.ollama_host,
        "--openai-base-url",
        openai_base_url,
        "--include-timestamps",
        args.include_timestamps,
        "--output-format",
        args.output_format,
    ]
    if openai_api_key:
        cmd.extend(["--openai-api-key", openai_api_key])
    if args.out:
        cmd.extend(["--out", args.out])
    if args.cookies:
        cmd.extend(["--cookies", args.cookies])
    if args.verbose:
        cmd.append("--verbose")
    return cmd


def build_transcript_cmd(args: argparse.Namespace) -> list[str]:
    """Build uvx command for transcript-only extraction (no LLM summarization).

    This is used when the handler detects it is running inside a CLI agent
    (Claude Code, Codex, OpenCode) — the calling agent handles LLM work.
    """
    spec = SILENTIR_SPEC
    if args.silentir_version:
        spec = f"silentir[asr]=={args.silentir_version}"

    cmd: list[str] = [
        "uvx",
        "--from",
        spec,
        "silentir",
        args.source,
        "--transcript-only",
        "--language",
        args.language,
    ]
    if args.cookies:
        cmd.extend(["--cookies", args.cookies])
    if args.verbose:
        cmd.append("--verbose")
    return cmd


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if shutil.which("uvx") is None:
        emit_failure(
            FailureReport(
                category="missing_uvx",
                exit_code=EXIT_MISSING_UVX,
                detail="'uvx' is not on PATH.",
                ask_user=[
                    "Please install `uv` (which ships `uvx`) — see "
                    "https://docs.astral.sh/uv/getting-started/installation/ — then "
                    "re-run.",
                ],
                remediations=[
                    "macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`.",
                    "Homebrew: `brew install uv`.",
                ],
            )
        )
        return EXIT_MISSING_UVX

    pre = preflight(args)
    if pre is not None:
        emit_failure(pre)
        return pre.exit_code

    agent = _detect_agent()
    if agent:
        cmd = build_transcript_cmd(args)
    else:
        cmd = build_uvx_cmd(args)
    try:
        proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, check=False)
    except FileNotFoundError as exc:
        emit_failure(
            FailureReport(
                category="missing_uvx",
                exit_code=EXIT_MISSING_UVX,
                detail=f"failed to launch uvx: {exc}",
            )
        )
        return EXIT_MISSING_UVX

    # Forward whatever silentir wrote to stderr so logs remain visible.
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()

    if proc.returncode == EXIT_OK:
        return EXIT_OK

    report = classify(proc.returncode, proc.stderr or "", args)
    emit_failure(report)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
