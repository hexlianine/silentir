from __future__ import annotations

import argparse
import sys

from .api import generate_notes
from .exceptions import (
    ConfigurationError,
    ModelInferenceError,
    TranscriptExtractionError,
    UnsupportedURLError,
)
from .logging import LoggingSettings, setup_logger
from .noters import default_noter_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate structured notes from video URLs")
    parser.add_argument("url", help="YouTube or Bilibili video URL")
    parser.add_argument("--language", default="auto", help="Target language or 'auto'")
    parser.add_argument(
        "--provider-policy",
        default="local_first",
        choices=["local_first", "online_first", "local_only", "online_only"],
    )
    parser.add_argument(
        "--output-format",
        default="markdown",
        choices=["markdown", "text", "json"],
    )
    parser.add_argument(
        "--include-timestamps",
        default="section",
        choices=["section", "point", "none"],
    )
    parser.add_argument("--local-model", default="qwen2.5:7b-instruct")
    parser.add_argument("--online-model", default="gpt-4.1-mini")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--openai-base-url", default="https://api.openai.com/v1")
    parser.add_argument("--openai-api-key", default=None)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    # The 'action' parameter in argparse determines how the command-line argument should be handled.
    # When using action="store_true", argparse will store the value True if the flag is present,
    # and False if it is absent. This is typically used for boolean flags.
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--log-format", default=None)
    parser.add_argument("--log-date-format", default=None)
    parser.add_argument("--log-file", default=None)
    parser.add_argument("--out", dest="out", default=None, help="Optional output file path")
    parser.add_argument("--cookies", dest="cookies", default=None, help="Optional cookies.txt path")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    setup_logger(
        LoggingSettings(
            log_level=args.log_level,
            verbose=args.verbose,
            log_format=args.log_format,
            log_date_format=args.log_date_format,
            log_file=args.log_file,
        )
    )

    try:
        result = generate_notes(
            args.url,
            language=args.language,
            output_format=args.output_format,
            provider_policy=args.provider_policy,
            local_model=args.local_model,
            online_model=args.online_model,
            ollama_host=args.ollama_host,
            openai_base_url=args.openai_base_url,
            openai_api_key=args.openai_api_key,
            include_timestamps=args.include_timestamps,
            write_path=args.out,
            cookies_path=args.cookies,
        )
    except (UnsupportedURLError, ConfigurationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    except TranscriptExtractionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(3)
    except ModelInferenceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(4)

    rendered = default_noter_registry().note(args.output_format, result)
    print(rendered, end="")


if __name__ == "__main__":
    main()
