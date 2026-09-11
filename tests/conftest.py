from __future__ import annotations

import json
import os
from base64 import b64encode
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

os.environ.setdefault("WOVN_SECRET_KEY", "unit-test-secret-key")
os.environ.setdefault("WOVN_GITHUB_CLIENT_ID", "test-client-id")
os.environ.setdefault("WOVN_GITHUB_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("WOVN_TESTING", "1")

SESSION_COOKIE = "wovn_session"
SESSION_SECRET = "unit-test-secret-key"


def set_session_user(client: TestClient, user_id: str) -> None:
    signer = TimestampSigner(str(SESSION_SECRET))
    payload = b64encode(json.dumps({"user_id": user_id}).encode("utf-8"))
    client.cookies.set(SESSION_COOKIE, signer.sign(payload).decode("utf-8"))


def clear_session(client: TestClient) -> None:
    client.cookies.delete(SESSION_COOKIE)


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("WOVN_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WOVN_DATABASE_URL", f"sqlite:///{tmp_path / 'wovn.db'}")
    monkeypatch.setenv("WOVN_TESTING", "1")

    from api.config import settings
    from api.db import reset_engine
    from api.jobs.rate_limit import job_rate_limiter
    from api.main import app

    settings.data_dir = tmp_path
    settings.database_url = f"sqlite:///{(tmp_path / 'wovn.db').resolve()}"
    settings.testing = True
    settings.github_client_id = "test-client-id"
    settings.github_client_secret = "test-client-secret"
    reset_engine()
    job_rate_limiter.reset()

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_a(client: TestClient) -> dict:
    from api.jobs import store

    user = store.upsert_github_user(
        github_id=101,
        email="a@example.com",
        display_name="Ada",
        access_token="gho_aaa",
        refresh_token="refresh_aaa",
        expires_at=None,
    )
    set_session_user(client, user["id"])
    return user


@pytest.fixture
def user_b(client: TestClient) -> dict:
    from api.jobs import store

    return store.upsert_github_user(
        github_id=202,
        email="b@example.com",
        display_name="Bob",
        access_token="gho_bbb",
        refresh_token=None,
        expires_at=None,
    )


@pytest.fixture
def login_as(client: TestClient):
    def _login(user: dict) -> None:
        set_session_user(client, user["id"])

    return _login
