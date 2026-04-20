from __future__ import annotations

from abc import ABC, abstractmethod

from ..exceptions import ModelInferenceError


class ChatProvider(ABC):
    name: str

    @abstractmethod
    def chat(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> str:
        raise NotImplementedError


class ProviderUnavailable(ModelInferenceError):
    """Provider is not configured or reachable."""
