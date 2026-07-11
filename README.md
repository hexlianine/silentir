# silentir

The `silentir` project generates structured notes from YouTube and Bilibili URLs using local (`Ollama`) or online (`OpenAI-compatible`) models.

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
uv run silentir "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --provider-policy local_first \
  --output-format markdown \
  --include-timestamps section \
  --out notes.md
```

## Python API

```python
from silentir import generate_notes

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

## Bilibili Subtitles (Optional)

For Bilibili URLs, subtitle extraction prefers [`bilibili-cli`](https://github.com/public-clis/bilibili-cli) (`bili`) when available, because Bilibili subtitles require authentication and use a private format that `yt-dlp` cannot reliably fetch. If `bili` is missing or fails, silentir automatically falls back to `yt-dlp`.

Install and authenticate (one time):

```bash
uv tool install bilibili-cli
bili login   # QR login, or auto-uses browser cookies
```

Control the backend explicitly with `--bilibili-backend`:

- `auto` (default): try `bili`, fall back to `yt-dlp`
- `bili`: use `bili` only; fail if unavailable
- `ytdlp`: use `yt-dlp` only, skip `bili`

`bili` uses its own credential store (`~/.bilibili-cli/`). The `--cookies` flag applies only to the `yt-dlp` fallback path.

## Streamlit UI

Run the web UI:

```bash
uv run --extra ui,asr streamlit run examples/basic_ui.py
```

The UI exposes the same configuration options as the CLI and lets you preview and download generated notes.
You can also provide an optional `write path` to persist the rendered notes directly to a file.

## Skill

`silentir` ships an agent skill so Claude Code (and other runtimes that read `~/.agents/skills/`) can call it via a slash command.

### Quick install

```bash
# Install as `/silentir` (default)
bash scripts/install-skill.sh

# Install under a custom slash-command name
bash scripts/install-skill.sh --name video-notes
# -> /video-notes source="<URL or local file path>"

# Development mode: symlink instead of copy
bash scripts/install-skill.sh --symlink

# Remove an install
bash scripts/install-skill.sh --uninstall --name video-notes
```

The script copies (or symlinks) the skill into `~/.agents/skills/<name>/` and creates a `~/.claude/skills/<name>` symlink. The installed `SKILL.md`'s `name:` field is rewritten when you pass `--name` so the slash command matches. `bash scripts/install-skill.sh --help` lists every flag. Override `AGENTS_SKILLS_DIR` / `CLAUDE_SKILLS_DIR` env vars to target a non-default location.

### Requirements

- `uvx` on `$PATH` ([install uv](https://docs.astral.sh/uv/getting-started/installation/)). The handler launches the published `silentir[asr]` package from PyPI; no local checkout is needed.
- Optional env defaults: `LOCAL_MODEL`, `ONLINE_MODEL`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`.

**Skill files:**
- [skills/silentir/SKILL.md](skills/silentir/SKILL.md): manifest, description, and argument doc.
- [skills/silentir/handler.py](skills/silentir/handler.py): execution wrapper (shells out to `uvx --from "silentir[asr]" silentir …`).
- [scripts/install-skill.sh](scripts/install-skill.sh): install / uninstall utility (kept outside the skill payload).
