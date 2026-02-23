"""Basic Usage"""

import os

from silent import generate_notes
from silent.logging import LoggingSettings, setup_logger

if __name__ == "__main__":
    setup_logger(
        LoggingSettings(
            verbose=True,
        )
    )
    result = generate_notes(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        language="auto",
        provider_policy="local_first",
        ollama_host="http://localhost:11434",
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        local_model=os.getenv("LOCAL_MODEL", "qwen2.5:7b-instruct"),
        online_model=os.getenv("ONLINE_MODEL", "qwen/qwen3-235b-a22b-thinking-2507"),
        include_timestamps="section",
    )
    print(result.note_markdown)
