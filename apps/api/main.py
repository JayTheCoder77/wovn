from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.config import settings
from api.db import init_db
from api.jobs.worker import worker_loop
from api.routes.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.jobs import router as jobs_router
from api.routes.repos import router as repos_router
from api.routes.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = None
    if not settings.testing:
        task = asyncio.create_task(worker_loop())
    yield
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Wovn API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="wovn_session",
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 24 * 14,
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(repos_router)
app.include_router(jobs_router)


def run() -> None:
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
