from __future__ import annotations

from pydantic import BaseModel, Field


class SubmitJobRequest(BaseModel):
    repo_url: str = Field(..., min_length=12, max_length=400)


class ConfirmJobRequest(BaseModel):
    model: str | None = None


class SettingsUpdate(BaseModel):
    groq_api_key: str | None = None
    default_model: str | None = None
    max_tokens: int | None = Field(default=None, ge=1000, le=2_000_000)
