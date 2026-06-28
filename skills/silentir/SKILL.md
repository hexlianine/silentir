---
name: silentir
description: Use when the user wants structured notes, a summary, key takeaways, or a transcript from a video — given either a YouTube/Bilibili URL or a local video/audio file path (mp4, mkv, webm, mov, m4a, mp3, …), including lecture recordings, podcasts, or talks. Handles native-subtitle fallback to Whisper ASR and supports local (Ollama) or online (OpenAI-compatible) summarization.
user-invocable: true
metadata:
  {"requires": {"bins": ["python3", "uvx"]}}
---

# Silentir Video Notes

Generate high-quality, structured Markdown notes from a video. The same skill works for remote videos (YouTube, Bilibili) and for local media files on disk — the underlying recorder is chosen automatically from the `source` value.

**Invocation:** `/silentir source="<URL or local file path>" [language="…"] [local_model="…"] [online_model="…"] [provider_policy="…"] [verbose=true]`

## How to use

Invoke `/silentir` when the user provides any of the following and wants a summary, key takeaways, transcript, or structured notes:

- A YouTube URL (`youtube.com`, `youtu.be`, `m.youtube.com`)
- A Bilibili URL (`bilibili.com`, `b23.tv`)
- A local file path to a video (mp4, mkv, webm, avi, mov, flv, wmv, m4v, ts, mpg, mpeg, 3gp) — the file must exist on disk
- A local file path to an audio recording — accepted when the file exists on disk (extension is not enough on its own)

### Arguments
- `source`: YouTube/Bilibili URL **or** local video/audio file path. (Positional; required.)
- `language`: optional, e.g., `"en"`, `"zh"`, or `"auto"` (default `"auto"`).
- `local_model`: optional, Ollama model name (e.g., `"qwen2.5:7b-instruct"`).
- `online_model`: optional, OpenAI-compatible model name.
- `provider_policy`: optional, one of `local_first`, `online_first`, `local_only`, `online_only` (default `local_first`).
- `ollama_host`: optional, defaults to `http://localhost:11434`.
- `verbose`: optional flag, enables debug logging including which recorder was matched.

`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `LOCAL_MODEL`, and `ONLINE_MODEL` are also read from the environment when the matching argument is omitted.

## Runtime

The handler runs the published `silentir` package from PyPI via `uvx`, with the `[asr]` extra so Whisper-based transcription is available. No local checkout of the project is required — only `uvx` (ships with [`uv`](https://docs.astral.sh/uv/)) on `$PATH`. The first invocation ephemerally downloads silentir and its dependencies; subsequent invocations reuse the cached environment.

## Behavior notes

- Inputs are routed automatically: HTTPS URLs go through the YouTube or Bilibili recorder; other strings are treated as local paths. An unsupported string raises `UnsupportedURLError`.
- For local files, the pipeline always runs Whisper ASR (subtitles aren't available off-disk). Missing local file paths and missing cookies paths are caught up front by handler preflight and surface as `unsupported_source` failures, not opaque Whisper errors.
- For remote URLs, native subtitles are tried first; ASR is the fallback.

## Error handling

When the underlying pipeline fails, the handler emits a structured remediation block on **stderr** between the markers `=== silentir failed ===` and `=== end silentir failure ===`. Each block carries:

- `category:` one of `unsupported_source`, `configuration`, `transcript_extraction`, `model_inference`, `missing_uvx`, `unknown`.
- `exit_code:` the non-zero process exit (2, 3, 4, or 127).
- `detail:` the raw error line from upstream.
- `ask_user:` a bulleted list of specific questions the agent should put to the user before retrying.
- `remediations:` concrete commands or flag changes the user can apply.

**When this skill returns a non-zero exit, the agent MUST:**

1. Surface the `detail:` line to the user verbatim.
2. Pick the most relevant question from `ask_user:` and ask it — do **not** invent values for missing API keys, cookies paths, or model names.
3. Once the user replies, re-invoke `/silentir` with the supplied data (set env vars, pass `--cookies`, change `--provider-policy`, etc.).

A subset of failures is caught **before** `uvx` is invoked (missing local file, missing cookies file, `online_only` policy with no API key, `local_only` policy with no model). These also produce the same remediation block format, so the agent can use a single parsing path.

## Invocation examples

```bash
# Remote video
/silentir source="https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Local lecture recording
/silentir source="/Users/me/recordings/lecture.mp4" language="en"

# Local audio podcast with a chosen Ollama model
/silentir source="/tmp/podcast.m4a" local_model="qwen2.5:7b-instruct"
```
