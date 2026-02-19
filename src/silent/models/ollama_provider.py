from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .base import ChatProvider, ProviderUnavailable


class OllamaProvider(ChatProvider):
    name = "local"

    def __init__(self, host: str = "http://localhost:11434") -> None:
        self.host = host.rstrip("/")

    def chat(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> str:
        payload = {
            "model": model,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        req = Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ProviderUnavailable(f"Ollama request failed: {exc}") from exc

        message = (data.get("message") or {}).get("content", "")
        if not message:
            raise ProviderUnavailable("Ollama returned empty content.")
        return message
