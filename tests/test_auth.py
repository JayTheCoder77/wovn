from __future__ import annotations

from urllib.parse import unquote


def test_unauthenticated_jobs_returns_401(client):
    response = client.get("/jobs")
    assert response.status_code == 401


def test_unauthenticated_settings_returns_401(client):
    response = client.get("/settings")
    assert response.status_code == 401


def test_github_login_redirects_to_github(client):
    response = client.get("/auth/github/login", follow_redirects=False)
    assert response.status_code == 302
    location = unquote(response.headers["location"])
    assert "github.com/login/oauth/authorize" in location
    assert "read:user" in location
    assert "repo" in location


def test_github_callback_sets_session_and_me(client, monkeypatch):
    from api.auth import oauth as oauth_mod

    async def fake_authorize_access_token(request):
        return {
            "access_token": "gho_from_github",
            "refresh_token": "refresh_from_github",
            "expires_at": None,
        }

    class FakeResponse:
        def json(self):
            return {"id": 4242, "login": "octocat", "email": "octocat@github.com", "name": "The Octocat"}

        def raise_for_status(self):
            return None

    async def fake_get(url, token=None):
        return FakeResponse()

    monkeypatch.setattr(oauth_mod.oauth.github, "authorize_access_token", fake_authorize_access_token)
    monkeypatch.setattr(oauth_mod.oauth.github, "get", fake_get)

    response = client.get("/auth/github/callback?code=abc", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].rstrip("/") in {"http://localhost:3000", "http://localhost:3000/"}

    me = client.get("/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["display_name"] == "The Octocat"
    assert body["github_id"] == 4242
    assert "id" in body


def test_logout_clears_session(client, user_a):
    me = client.get("/auth/me")
    assert me.status_code == 200
    logout = client.post("/auth/logout")
    assert logout.status_code == 204
    set_cookie = logout.headers.get("set-cookie", "")
    assert "wovn_session=" in set_cookie
    client.cookies.clear()
    me_after = client.get("/auth/me")
    assert me_after.status_code == 401
