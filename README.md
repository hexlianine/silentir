# silent

The `silent` project generates structured notes from YouTube and Bilibili URLs using local (`Ollama`) or online (`OpenAI-compatible`) models.

## Install

```bash
uv sync
```

Optional ASR dependencies:

```bash
uv sync --extra asr
```

Optional example dependencies (`examples/basic_usage.py`):

```bash
uv sync --extra examples
```

Optional Streamlit UI dependencies:

```bash
uv sync --extra ui
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
    local_model="qwen2.5:7b-instruct",
    online_model="gpt-4.1-mini",
    ollama_host="http://localhost:11434",
    openai_base_url="https://api.openai.com/v1",
    openai_api_key=None,
)
print(result.note_markdown)
```

Run tests:

```bash
uv run pytest
```

## Lint And Format

Install Git hooks:

```bash
uv run pre-commit install
```

Run checks manually:

```bash
uv run pre-commit run --all-files
uv run ruff check .
uv run ruff format .
```

Architecture and pipeline details:

- `docs/architecture.md`

## Explicit Configuration

All runtime configuration is explicit. Use CLI flags or Python function arguments instead of environment variables.

## Notes

- Subtitle-first transcription is used by default.
- If subtitles are unavailable, ASR transcriber fallback is used.
- Runtime provider fallback follows `provider_policy`.

## Streamlit UI

Run the web UI:

```bash
uv run --extra ui streamlit run examples/basic_ui.py
```

The UI exposes the same configuration options as the CLI and lets you preview and download generated notes.
You can also provide an optional `write path` to persist the rendered notes directly to a file.

## Skill

`silent` can be used as an skill.

1. Ensure `silent` is installed in the agent's environment.
2. Copy the `skills/silent` directory to your skills folder.
3. The agent can then use the `/silent` command to process video URLs.

**Skill files:**
- `skills/silent/SKILL.md`: Manifest and metadata.
- `skills/silent/handler.py`: Execution wrapper.
