from __future__ import annotations

from types import SimpleNamespace

from generation.llm import LLMClient, LLMProvider


def mock_openrouter_models(monkeypatch):
    class FakeModels:
        def get(self, *, author: str, slug: str):
            model_id = f"{author}/{slug}"
            if model_id == "unknown/model":
                error = RuntimeError("not found")
                error.status_code = 404
                raise error
            return SimpleNamespace(
                data=SimpleNamespace(
                    id=model_id,
                    name=f"Model {model_id}",
                    pricing=SimpleNamespace(prompt="0.000001", completion="0.000002"),
                )
            )

    class FakeOpenRouter:
        def __init__(self, *args, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr("estimator.pricing.OpenRouter", FakeOpenRouter)


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


def test_provider_keys_and_defaults_are_stored_independently(client, user_a, monkeypatch):
    mock_openrouter_models(monkeypatch)
    groq = client.put("/settings", json={"groq_api_key": "gsk_saved", "default_model": "openai/gpt-oss-120b"})
    assert groq.status_code == 200

    router = client.put(
        "/settings",
        json={
            "llm_provider": "openrouter",
            "openrouter_api_key": "sk-or-saved",
            "default_model": "google/gemini-2.5-flash",
        },
    )
    assert router.status_code == 200
    assert router.json()["has_groq_key"] is True
    assert router.json()["has_openrouter_key"] is True
    assert router.json()["llm_provider"] == "openrouter"
    assert router.json()["default_model"] == "google/gemini-2.5-flash"

    back = client.put("/settings", json={"llm_provider": "groq"})
    assert back.json()["has_groq_key"] is True
    assert back.json()["has_openrouter_key"] is True
    assert back.json()["default_model"] == "openai/gpt-oss-120b"


def test_models_and_model_validation_are_provider_specific(client, user_a, monkeypatch):
    mock_openrouter_models(monkeypatch)
    groq_models = client.get("/models?provider=groq").json()
    router_models = client.get("/models?provider=openrouter").json()
    assert {model["id"] for model in groq_models}.isdisjoint({model["id"] for model in router_models})
    assert all("input_per_million" in model and "output_per_million" in model for model in router_models)

    invalid = client.put(
        "/settings",
        json={"llm_provider": "openrouter", "default_model": "unknown/model"},
    )
    assert invalid.status_code == 400


def test_openrouter_model_info_validates_custom_model_and_returns_live_pricing(client, user_a, monkeypatch):
    mock_openrouter_models(monkeypatch)

    valid = client.post("/models/info", json={"provider": "openrouter", "model": "anthropic/claude-sonnet-4"})
    assert valid.status_code == 200
    assert valid.json() == {
        "id": "anthropic/claude-sonnet-4",
        "label": "Model anthropic/claude-sonnet-4",
        "input_per_million": 1.0,
        "output_per_million": 2.0,
        "default": False,
    }

    invalid = client.post("/models/info", json={"provider": "openrouter", "model": "unknown/model"})
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
