from __future__ import annotations

from openrouter import OpenRouter

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
}

DEFAULT_MODEL = "openai/gpt-oss-20b"
DEFAULT_MODELS = {LLMProvider.GROQ: DEFAULT_MODEL, LLMProvider.OPENROUTER: "openai/gpt-4o-mini"}
OPENROUTER_DEFAULT_MODELS = (
    "openai/gpt-4o-mini",
    "google/gemini-2.5-flash",
    "anthropic/claude-haiku-4.5",
)


class OpenRouterModelError(ValueError):
    """A model ID could not be resolved through OpenRouter."""


class OpenRouterLookupError(RuntimeError):
    """OpenRouter could not be reached to resolve current model metadata."""


def _openrouter_model_parts(model_id: str) -> tuple[str, str]:
    normalized = model_id.strip()
    if not normalized or any(character.isspace() for character in normalized) or "/" not in normalized:
        raise OpenRouterModelError("Enter a full OpenRouter model ID, for example openai/gpt-4o-mini.")
    author, slug = normalized.split("/", 1)
    if not author or not slug:
        raise OpenRouterModelError("Enter a full OpenRouter model ID, for example openai/gpt-4o-mini.")
    return author, slug


def resolve_openrouter_model(model_id: str) -> dict[str, object]:
    """Validate a model ID and retrieve its current public token prices via the SDK."""
    author, slug = _openrouter_model_parts(model_id)
    try:
        response = OpenRouter().models.get(author=author, slug=slug)
        data = response.data
        input_per_million = float(data.pricing.prompt) * 1_000_000
        output_per_million = float(data.pricing.completion) * 1_000_000
    except (TypeError, ValueError) as exc:
        raise OpenRouterModelError(f"OpenRouter returned invalid pricing for {model_id.strip()}.") from exc
    except Exception as exc:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        if status_code == 404:
            raise OpenRouterModelError(f"OpenRouter model not found: {model_id.strip()}") from exc
        raise OpenRouterLookupError("Could not validate the model with OpenRouter. Please try again.") from exc

    return {
        "id": data.id,
        "label": data.name,
        "input_per_million": input_per_million,
        "output_per_million": output_per_million,
        "default": data.id in OPENROUTER_DEFAULT_MODELS,
    }


def list_models(provider: LLMProvider = LLMProvider.GROQ) -> list[dict[str, object]]:
    if provider is LLMProvider.OPENROUTER:
        return [resolve_openrouter_model(model_id) for model_id in OPENROUTER_DEFAULT_MODELS]
    rows = []
    for model_id, meta in MODELS[provider].items():
        rows.append({"id": model_id, **meta})
    return rows


def get_model(model_id: str, provider: LLMProvider = LLMProvider.GROQ) -> dict[str, object]:
    if provider is LLMProvider.OPENROUTER:
        return resolve_openrouter_model(model_id)
    if model_id not in MODELS[provider]:
        raise KeyError(f"Unknown or unpriced {provider.value.title()} model: {model_id}")
    return {"id": model_id, **MODELS[provider][model_id]}


def estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int, provider: LLMProvider = LLMProvider.GROQ) -> float:
    meta = get_model(model_id, provider)
    cost = (
        (input_tokens / 1_000_000) * float(meta["input_per_million"])
        + (output_tokens / 1_000_000) * float(meta["output_per_million"])
    )
    return round(cost, 6)
