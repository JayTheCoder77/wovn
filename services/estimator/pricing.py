from __future__ import annotations

# Groq published self-serve prices as of 2026-09 (USD per 1M tokens).
# Enterprise / contact-sales models are omitted because cost cannot be estimated.
MODELS: dict[str, dict[str, object]] = {
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
}

DEFAULT_MODEL = "openai/gpt-oss-20b"


def list_models() -> list[dict[str, object]]:
    rows = []
    for model_id, meta in MODELS.items():
        rows.append({"id": model_id, **meta})
    return rows


def get_model(model_id: str) -> dict[str, object]:
    if model_id not in MODELS:
        raise KeyError(f"Unknown or unpriced Groq model: {model_id}")
    return MODELS[model_id]


def estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    meta = get_model(model_id)
    cost = (
        (input_tokens / 1_000_000) * float(meta["input_per_million"])
        + (output_tokens / 1_000_000) * float(meta["output_per_million"])
    )
    return round(cost, 6)
