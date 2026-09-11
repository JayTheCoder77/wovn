from __future__ import annotations

from generation.llm import LLMProvider

# Published self-serve prices as of 2026-09 (USD per 1M tokens).
# Enterprise/contact-sales and models without stable pricing are omitted.
MODELS: dict[LLMProvider, dict[str, dict[str, object]]] = {
    LLMProvider.GROQ: {
    "openai/gpt-oss-20b": {
        "label": "GPT OSS 20B",
        "input_per_million": 0.075,
        "output_per_million": 0.30,
        "default": True,
    },
    "openai/gpt-oss-120b": {
        "label": "GPT OSS 120B",
        "input_per_million": 0.15,
        "output_per_million": 0.60,
        "default": False,
    },
    "qwen/qwen3.6-27b": {
        "label": "Qwen 3.6 27B",
        "input_per_million": 0.60,
        "output_per_million": 3.00,
        "default": False,
    },
    "qwen/qwen3.8-27b": {
        "label": "Qwen 3.8 27B",
        "input_per_million": 0.80,
        "output_per_million": 4.00,
        "default": False,
    },
    },
    LLMProvider.OPENROUTER: {
        "openai/gpt-4o-mini": {"label": "GPT-4o Mini", "input_per_million": 0.15, "output_per_million": 0.60, "default": True},
        "google/gemini-2.0-flash-001": {"label": "Gemini 2.0 Flash", "input_per_million": 0.10, "output_per_million": 0.40, "default": False},
        "anthropic/claude-3.5-haiku": {"label": "Claude 3.5 Haiku", "input_per_million": 0.80, "output_per_million": 4.00, "default": False},
    },
}

DEFAULT_MODEL = "openai/gpt-oss-20b"
DEFAULT_MODELS = {LLMProvider.GROQ: DEFAULT_MODEL, LLMProvider.OPENROUTER: "openai/gpt-4o-mini"}


def list_models(provider: LLMProvider = LLMProvider.GROQ) -> list[dict[str, object]]:
    rows = []
    for model_id, meta in MODELS[provider].items():
        rows.append({"id": model_id, **meta})
    return rows


def get_model(model_id: str, provider: LLMProvider = LLMProvider.GROQ) -> dict[str, object]:
    if model_id not in MODELS[provider]:
        raise KeyError(f"Unknown or unpriced {provider.value.title()} model: {model_id}")
    return MODELS[provider][model_id]


def estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int, provider: LLMProvider = LLMProvider.GROQ) -> float:
    meta = get_model(model_id, provider)
    cost = (
        (input_tokens / 1_000_000) * float(meta["input_per_million"])
        + (output_tokens / 1_000_000) * float(meta["output_per_million"])
    )
    return round(cost, 6)
