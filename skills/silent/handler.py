#!/usr/bin/env python3
import argparse
import os
import sys

from silent import generate_notes
from silent.logging import LoggingSettings, setup_logger


def main():
    parser = argparse.ArgumentParser(description="Silent Skill Handler")
    parser.add_argument("url", help="URL of the video to process")
    parser.add_argument("--language", default="auto", help="Language for notes")
    parser.add_argument("--local-model", help="Local Ollama model name")
    parser.add_argument("--online-model", help="Online OpenAI model name")
    parser.add_argument("--provider-policy", default="local_first", help="Provider policy")
    parser.add_argument("--ollama-host", default="http://localhost:11434", help="Ollama host URL")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logger(LoggingSettings(verbose=args.verbose))

    try:
        # Get models from environment if not provided via CLI
        local_model = args.local_model or os.getenv("LOCAL_MODEL")
        online_model = args.online_model or os.getenv("ONLINE_MODEL")

        if not local_model and not online_model:
            # Fallback to some defaults if nothing is set
            local_model = "qwen2.5:7b-instruct"

        result = generate_notes(
            url=args.url,
            language=args.language,
            provider_policy=args.provider_policy,
            local_model=local_model,
            online_model=online_model,
            ollama_host=args.ollama_host,
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            include_timestamps="section",
        )

        print(result.note_markdown)

    except Exception as e:
        print(f"Error generating notes: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
