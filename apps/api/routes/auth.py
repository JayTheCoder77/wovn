from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from api.auth.deps import get_current_user
from api.auth.github_api import _expires_at_from_token
from api.auth.oauth import oauth
from api.config import settings
from api.jobs import store

router = APIRouter()


@router.get("/auth/github/login")
async def github_login(request: Request):
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    return await oauth.github.authorize_redirect(request, settings.github_callback_url)


@router.get("/auth/github/callback")
async def github_callback(request: Request):
    if request.query_params.get("error"):
        raise HTTPException(status_code=400, detail="GitHub login failed")
    token = await oauth.github.authorize_access_token(request)
    profile_response = await oauth.github.get("user", token=token)
    profile = profile_response.json()
    user = store.upsert_github_user(
        github_id=int(profile["id"]),
        email=profile.get("email"),
        display_name=profile.get("name") or profile.get("login") or "GitHub user",
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        expires_at=_expires_at_from_token(token),
    )
    request.session["user_id"] = user["id"]
    return RedirectResponse(settings.web_origin_url, status_code=302)


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "github_id": user["github_id"],
        "email": user["email"],
        "display_name": user["display_name"],
    }


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    response = Response(status_code=204)
    response.delete_cookie("wovn_session", path="/")
    return response
