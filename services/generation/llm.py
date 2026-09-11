from __future__ import annotations

import asyncio
import random
from enum import Enum
from typing import Any

from groq import AsyncGroq
from openrouter import OpenRouter


class LLMProvider(str, Enum):
    GROQ = "groq"
    OPENROUTER = "openrouter"


class LLMClient:
    """Provider-neutral chat client with a per-run token cap."""

    def __init__(self, provider: LLMProvider, api_key: str, model: str, max_tokens_remaining: int):
        self.provider = provider
        self.model = model
        self.max_tokens_remaining = max_tokens_remaining
        self.tokens_used = 0
        self._client: Any = (
            AsyncGroq(api_key=api_key) if provider is LLMProvider.GROQ else OpenRouter(api_key=api_key)
        )

    def _charge(self, usage: Any) -> None:
        if usage is None:
            return
        prompt = getattr(usage, "prompt_tokens", 0) or 0
        completion = getattr(usage, "completion_tokens", 0) or 0
        used = prompt + completion
        self.tokens_used += used
        self.max_tokens_remaining -= used
        if self.max_tokens_remaining < 0:
            raise RuntimeError("Token cap reached for this run.")

    async def complete(
        self,
        *,
        system: str,
        user: str,
        json_mode: bool = True,
        max_completion_tokens: int = 2048,
    ) -> str:
        if self.max_tokens_remaining <= 0:
            raise RuntimeError("Token cap reached for this run.")

        delay = 1.0
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": 0.2,
                    "max_tokens": min(max_completion_tokens, max(256, self.max_tokens_remaining)),
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                if self.provider is LLMProvider.GROQ:
                    response = await self._client.chat.completions.create(**kwargs)
                else:
                    response = await self._client.chat.send_async(**kwargs)
                self._charge(getattr(response, "usage", None))
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
                if status_code in {429, 500, 502, 503} and attempt < 4:
                    await asyncio.sleep(delay + random.random())
                    delay = min(delay * 2, 16)
                    continue
                raise
        raise last_error or RuntimeError(f"{self.provider.value} request failed")
