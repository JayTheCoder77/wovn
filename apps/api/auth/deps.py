from __future__ import annotations

from fastapi import HTTPException, Request

from api.jobs import store


def get_current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = store.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
