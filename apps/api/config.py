from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="WOVN_")

    data_dir: Path = Path("./data")
    secret_key: str = "wovn-dev-secret-change-me"
    cors_origins: str = "http://localhost:3000"
    max_tokens_default: int = 200_000
    database_url: str | None = None
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://127.0.0.1:8000/auth/github/callback"
    web_origin: str = ""
    testing: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def web_origin_url(self) -> str:
        if self.web_origin.strip():
            return self.web_origin.strip().rstrip("/")
        origins = self.cors_origin_list or ["http://localhost:3000"]
        return origins[0].rstrip("/")


settings = Settings()
