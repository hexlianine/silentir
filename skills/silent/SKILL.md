---
name: silent
description: Generate structured notes and summaries from YouTube or Bilibili video URLs. It can handle both online and local models for transcription and summarization.
user-invocable: true
metadata:
  {"requires": {"bins": ["python3"]}}
---

# Silent Video Notes

The `silent` skill allows the agent to generate high-quality, structured notes from video URLs (YouTube/Bilibili).

## How to use

Invoke this skill when the user provides a video link and wants a summary, key takeaways, or detailed notes.

### Arguments
- `url`: The video URL (YouTube/Bilibili).
- `language`: optional, e.g., "en", "zh", or "auto".
- `local_model`: optional, Ollama model name (e.g., "qwen2.5:7b-instruct").
- `online_model`: optional, OpenAI-compatible model name.

## Example
`/silent url="https://www.youtube.com/watch?v=..."`
