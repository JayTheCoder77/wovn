from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth import github_api
from api.auth.deps import get_current_user
from api.jobs import store
from api.jobs.rate_limit import job_rate_limiter
from api.jobs.paths import doc_path
from api.jobs.worker import enqueue_analyze, new_job_id
from ingest.clone import CloneError, parse_github_url

router = APIRouter()


class RegisterRepoRequest(BaseModel):
    url: str = Field(..., min_length=12, max_length=400)


def _public_repo(repo: dict) -> dict:
    return {
        "id": repo["id"],
        "user_id": repo["user_id"],
        "provider": repo["provider"],
        "full_name": repo["full_name"],
        "default_url": repo["default_url"],
        "default_branch": repo.get("default_branch"),
        "visibility": repo["visibility"],
        "last_analyzed_at": repo.get("last_analyzed_at"),
    }


def _public_job(job: dict) -> dict:
    has_doc = False
    try:
        has_doc = doc_path(job["id"]).exists()
    except FileNotFoundError:
        has_doc = False
    return {**job, "has_doc": has_doc}


async def start_job_for_repo(user: dict, repo: dict) -> dict:
    if not job_rate_limiter.check(user["id"]):
        raise HTTPException(status_code=429, detail="Too many documentation jobs. Try again later.")
    job_id = new_job_id()
    job = store.create_job(job_id, user["id"], repo["id"], repo["default_url"])
    await enqueue_analyze(job_id)
    return _public_job(job)


@router.get("/repos")
async def list_repos(user: dict = Depends(get_current_user)):
    return [_public_repo(repo) for repo in store.list_repos(user["id"])]


@router.post("/repos")
async def register_repo(payload: RegisterRepoRequest, user: dict = Depends(get_current_user)):
    try:
        parsed = parse_github_url(payload.url)
    except CloneError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repo = store.upsert_repo(
        user["id"],
        full_name=f"{parsed.owner}/{parsed.name}",
        default_url=f"https://github.com/{parsed.owner}/{parsed.name}",
        visibility="unknown",
    )
    return _public_repo(repo)


@router.post("/repos/{repo_id}/jobs")
async def create_repo_job(repo_id: str, user: dict = Depends(get_current_user)):
    repo = store.get_repo(user["id"], repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return await start_job_for_repo(user, repo)


@router.get("/github/repos")
async def github_repo_picker(user: dict = Depends(get_current_user)):
    try:
        token = github_api.valid_access_token(user["id"])
        return github_api.list_user_repos(token)
    except github_api.GitHubAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not list GitHub repositories") from exc
