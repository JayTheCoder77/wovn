from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth.deps import get_current_user
from api.auth.keys import encrypt_key
from api.jobs import store
from api.routes.schemas import ModelInfoRequest, SettingsUpdate
from estimator.pricing import DEFAULT_MODELS, OpenRouterLookupError, OpenRouterModelError, get_model, list_models
from generation.llm import LLMProvider

router = APIRouter()


@router.get("/models")
async def models(provider: LLMProvider = Query(LLMProvider.GROQ)):
    try:
        return await asyncio.to_thread(list_models, provider)
    except OpenRouterLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except OpenRouterModelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/models/info")
async def model_info(payload: ModelInfoRequest):
    try:
        provider = LLMProvider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Provider must be groq or openrouter") from exc
    try:
        return await asyncio.to_thread(get_model, payload.model, provider)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenRouterModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OpenRouterLookupError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _provider(row: dict) -> LLMProvider:
    try:
        return LLMProvider(row.get("llm_provider") or LLMProvider.GROQ.value)
    except ValueError:
        return LLMProvider.GROQ


def _default_model(row: dict, provider: LLMProvider) -> str:
    field = "default_model" if provider is LLMProvider.GROQ else "openrouter_default_model"
    return row.get(field) or DEFAULT_MODELS[provider]


@router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    row = store.get_settings(user["id"])
    provider = _provider(row)
    return {
        "has_groq_key": bool(row.get("groq_key_encrypted")),
        "has_openrouter_key": bool(row.get("openrouter_key_encrypted")),
        "llm_provider": provider.value,
        "default_model": _default_model(row, provider),
        "max_tokens": row.get("max_tokens"),
    }


@router.put("/settings")
async def put_settings(payload: SettingsUpdate, user: dict = Depends(get_current_user)):
    fields: dict = {}
    provider = _provider(store.get_settings(user["id"]))
    if payload.llm_provider is not None:
        try:
            provider = LLMProvider(payload.llm_provider)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Provider must be groq or openrouter") from exc
        fields["llm_provider"] = provider.value
    if payload.groq_api_key is not None:
        key = payload.groq_api_key.strip()
        if key:
            fields["groq_key_encrypted"] = encrypt_key(key)
        else:
            fields["groq_key_encrypted"] = None
    if payload.openrouter_api_key is not None:
        key = payload.openrouter_api_key.strip()
        fields["openrouter_key_encrypted"] = encrypt_key(key) if key else None
    if payload.default_model is not None:
        try:
            model = await asyncio.to_thread(get_model, payload.default_model, provider)
        except (KeyError, OpenRouterModelError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except OpenRouterLookupError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        fields["default_model" if provider is LLMProvider.GROQ else "openrouter_default_model"] = str(model["id"])
    if payload.max_tokens is not None:
        fields["max_tokens"] = payload.max_tokens
    if fields:
        store.update_settings(user["id"], **fields)
    return await get_settings(user)
