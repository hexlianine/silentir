from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .base import ChatProvider, ProviderUnavailable


class OpenAICompatibleProvider(ChatProvider):
    name = "online"

    def __init__(self, *, base_url: str, api_key: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def chat(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> str:
        if not self.api_key:
            raise ProviderUnavailable("OpenAI-compatible API key is not configured.")

        payload = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        req = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ProviderUnavailable(f"OpenAI-compatible request failed: {exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise ProviderUnavailable("OpenAI-compatible response missing choices.")
        content = (((choices[0] or {}).get("message") or {}).get("content") or "").strip()
        if not content:
            raise ProviderUnavailable("OpenAI-compatible response content is empty.")
        return content
