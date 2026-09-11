from __future__ import annotations

import asyncio
from types import SimpleNamespace

from generation.llm import LLMClient, LLMProvider


def test_openrouter_json_mode_requires_a_json_capable_provider(monkeypatch):
    request: dict = {}

    class FakeChat:
        async def send_async(self, **kwargs):
            request.update(kwargs)
            return SimpleNamespace(
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"purpose":"ok"}'))],
            )

    class FakeOpenRouter:
        def __init__(self, *, api_key: str):
            self.chat = FakeChat()

    monkeypatch.setattr("generation.llm.OpenRouter", FakeOpenRouter)

    client = LLMClient(LLMProvider.OPENROUTER, "sk-or-test", "openai/gpt-4o-mini", 1000)
    result = asyncio.run(client.complete(system="Return JSON.", user="Summarize."))

    assert result == '{"purpose":"ok"}'
    assert request["response_format"] == {"type": "json_object"}
    assert request["provider"] == {"require_parameters": True}
    assert request["reasoning"] == {"effort": "none"}


def test_openrouter_send_does_not_block_the_event_loop(monkeypatch):
    class FakeChat:
        async def send_async(self, **kwargs):
            await asyncio.sleep(0.1)
            return SimpleNamespace(
                usage=None,
                choices=[SimpleNamespace(message=SimpleNamespace(content="done"))],
            )

    class FakeOpenRouter:
        def __init__(self, *, api_key: str):
            self.chat = FakeChat()

    monkeypatch.setattr("generation.llm.OpenRouter", FakeOpenRouter)
    client = LLMClient(LLMProvider.OPENROUTER, "sk-or-test", "openai/gpt-4o-mini", 1000)

    async def run() -> bool:
        completion = asyncio.create_task(client.complete(system="Return text.", user="Summarize."))
        await asyncio.sleep(0.01)
        event_loop_was_responsive = not completion.done()
        assert await completion == "done"
        return event_loop_was_responsive

    assert asyncio.run(run())
