# silent

The `silent` project, which generates structured notes from YouTube and Bilibili URLs using local (`Ollama`) or online (`OpenAI-compatible`) models. or online LLMs. Added core functionality including environment configuration, CLI interface, and support for multiple output formats. Implemented video recording, transcription, and summarization features, along with necessary models and exception handling.

## Install

```bash
uv sync
```

Optional ASR dependencies:

```bash
uv sync --extra asr
```

Install dev/test dependencies:

```bash
uv sync --group dev
```

## Quickstart

```bash
uv run silent "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --provider-policy local_first \
  --output-format markdown \
  --include-timestamps section \
  --out notes.md
```

## Python API

```python
from silent import generate_notes

result = generate_notes(
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    language="auto",
    provider_policy="local_first",
)
print(result.note_markdown)
```

Run tests:

```bash
uv run pytest
```

## Environment Variables

- `VIDEO_NOTES_PROVIDER_POLICY`
- `VIDEO_NOTES_OLLAMA_HOST`
- `VIDEO_NOTES_OPENAI_BASE_URL`
- `VIDEO_NOTES_OPENAI_API_KEY`
- `VIDEO_NOTES_LOCAL_MODEL`
- `VIDEO_NOTES_ONLINE_MODEL`

## Notes

- Subtitle-first transcription is used by default.
- If subtitles are unavailable, ASR transcriber fallback is used.
- Runtime provider fallback follows `provider_policy`.
