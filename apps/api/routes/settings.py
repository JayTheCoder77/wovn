from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.auth.deps import get_current_user
from api.auth.keys import encrypt_key
from api.jobs import store
from api.routes.schemas import SettingsUpdate
from estimator.pricing import DEFAULT_MODEL, get_model, list_models

router = APIRouter()


@router.get("/models")
async def models():
    return list_models()


@router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    row = store.get_settings(user["id"])
    return {
        "has_groq_key": bool(row.get("groq_key_encrypted")),
        "default_model": row.get("default_model") or DEFAULT_MODEL,
        "max_tokens": row.get("max_tokens"),
    }


@router.put("/settings")
async def put_settings(payload: SettingsUpdate, user: dict = Depends(get_current_user)):
    fields: dict = {}
    if payload.groq_api_key is not None:
        key = payload.groq_api_key.strip()
        if key:
            fields["groq_key_encrypted"] = encrypt_key(key)
        else:
            fields["groq_key_encrypted"] = None
    if payload.default_model is not None:
        try:
            get_model(payload.default_model)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        fields["default_model"] = payload.default_model
    if payload.max_tokens is not None:
        fields["max_tokens"] = payload.max_tokens
    if fields:
        store.update_settings(user["id"], **fields)
    return await get_settings(user)
