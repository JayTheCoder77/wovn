from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Awaitable, Callable
from typing import Any

from groq import APIStatusError, AsyncGroq

ProgressCb = Callable[[str], Awaitable[None]] | Callable[[str], None] | None


class GroqClient:
    def __init__(self, api_key: str, model: str, max_tokens_remaining: int):
        self.model = model
        self.max_tokens_remaining = max_tokens_remaining
        self.tokens_used = 0
        self._client = AsyncGroq(api_key=api_key)

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
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                    "max_tokens": min(max_completion_tokens, max(256, self.max_tokens_remaining)),
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                response = await self._client.chat.completions.create(**kwargs)
                self._charge(response.usage)
                content = response.choices[0].message.content or ""
                return content
            except APIStatusError as exc:
                last_error = exc
                if exc.status_code in {429, 500, 502, 503} and attempt < 4:
                    await asyncio.sleep(delay + random.random())
                    delay = min(delay * 2, 16)
                    continue
                raise
        raise last_error or RuntimeError("Groq request failed")
