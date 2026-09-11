from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from api.auth.keys import decrypt_key
from api.config import settings
from api.jobs import store


class GitHubAuthError(Exception):
    pass


def list_user_repos(access_token: str) -> list[dict[str, Any]]:
    response = httpx.get(
        "https://api.github.com/user/repos",
        params={"per_page": 100, "sort": "updated", "affiliation": "owner,collaborator,organization_member"},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    response.raise_for_status()
    rows = []
    for item in response.json():
        private = bool(item.get("private"))
        rows.append(
            {
                "full_name": item["full_name"],
                "html_url": item.get("html_url") or f"https://github.com/{item['full_name']}",
                "visibility": item.get("visibility") or ("private" if private else "public"),
                "default_branch": item.get("default_branch"),
            }
        )
    return rows


def _expires_at_from_token(token: dict[str, Any]) -> datetime | None:
    if token.get("expires_at"):
        return datetime.fromtimestamp(int(token["expires_at"]), tz=timezone.utc)
    if token.get("expires_in"):
        return datetime.now(timezone.utc) + timedelta(seconds=int(token["expires_in"]))
    return None


def refresh_github_token(refresh_token: str) -> dict[str, Any]:
    response = httpx.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if "access_token" not in payload:
        raise GitHubAuthError("GitHub session expired. Reconnect GitHub and try again.")
    return payload


def valid_access_token(user_id: str) -> str:
    row = store.get_github_token(user_id)
    if row is None:
        raise GitHubAuthError("GitHub session expired. Reconnect GitHub and try again.")
    expires_at = row.get("expires_at")
    now = datetime.now(timezone.utc)
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            if not row.get("refresh_encrypted"):
                raise GitHubAuthError("GitHub session expired. Reconnect GitHub and try again.")
            refreshed = refresh_github_token(decrypt_key(row["refresh_encrypted"]))
            store.upsert_github_tokens(
                user_id,
                access_token=refreshed["access_token"],
                refresh_token=refreshed.get("refresh_token") or decrypt_key(row["refresh_encrypted"]),
                expires_at=_expires_at_from_token(refreshed),
            )
            return refreshed["access_token"]
    return decrypt_key(row["access_encrypted"])
