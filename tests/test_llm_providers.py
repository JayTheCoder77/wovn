from __future__ import annotations

from generation.llm import LLMClient, LLMProvider


def test_new_settings_default_to_groq(client, user_a):
    response = client.get("/settings")

    assert response.status_code == 200
    assert response.json() == {
        "has_groq_key": False,
        "has_openrouter_key": False,
        "llm_provider": "groq",
        "default_model": "openai/gpt-oss-20b",
        "max_tokens": 200000,
    }


def test_provider_keys_and_defaults_are_stored_independently(client, user_a):
    groq = client.put("/settings", json={"groq_api_key": "gsk_saved", "default_model": "openai/gpt-oss-120b"})
    assert groq.status_code == 200

    router = client.put(
        "/settings",
        json={
            "llm_provider": "openrouter",
            "openrouter_api_key": "sk-or-saved",
            "default_model": "google/gemini-2.0-flash-001",
        },
    )
    assert router.status_code == 200
    assert router.json()["has_groq_key"] is True
    assert router.json()["has_openrouter_key"] is True
    assert router.json()["llm_provider"] == "openrouter"
    assert router.json()["default_model"] == "google/gemini-2.0-flash-001"

    back = client.put("/settings", json={"llm_provider": "groq"})
    assert back.json()["has_groq_key"] is True
    assert back.json()["has_openrouter_key"] is True
    assert back.json()["default_model"] == "openai/gpt-oss-120b"


def test_models_and_model_validation_are_provider_specific(client, user_a):
    groq_models = client.get("/models?provider=groq").json()
    router_models = client.get("/models?provider=openrouter").json()
    assert {model["id"] for model in groq_models}.isdisjoint({model["id"] for model in router_models})
    assert all("input_per_million" in model and "output_per_million" in model for model in router_models)

    invalid = client.put(
        "/settings",
        json={"llm_provider": "openrouter", "default_model": groq_models[0]["id"]},
    )
    assert invalid.status_code == 400


def test_llm_client_selects_provider_sdk(monkeypatch):
    created: list[tuple[str, str]] = []

    class FakeGroq:
        def __init__(self, *, api_key: str):
            created.append(("groq", api_key))

    class FakeOpenRouter:
        def __init__(self, *, api_key: str):
            created.append(("openrouter", api_key))

    monkeypatch.setattr("generation.llm.AsyncGroq", FakeGroq)
    monkeypatch.setattr("generation.llm.OpenRouter", FakeOpenRouter)

    LLMClient(LLMProvider.GROQ, "gsk_test", "openai/gpt-oss-20b", 1000)
    LLMClient(LLMProvider.OPENROUTER, "sk-or-test", "openai/gpt-4o-mini", 1000)

    assert created == [("groq", "gsk_test"), ("openrouter", "sk-or-test")]
