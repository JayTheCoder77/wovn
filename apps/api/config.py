from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="WOVN_")

    data_dir: Path = Path("./data")
    secret_key: str = "wovn-dev-secret-change-me"
    cors_origins: str = "http://localhost:3000"
    max_tokens_default: int = 200_000

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
