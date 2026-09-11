from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.auth.deps import get_current_user
from api.jobs import store
from api.jobs.paths import doc_path, skeleton_path
from api.jobs.worker import enqueue_generate
from api.routes.repos import start_job_for_repo
from api.routes.schemas import ConfirmJobRequest, SubmitJobRequest
from estimator.estimate import estimate_job
from estimator.pricing import get_model
from ingest.clone import CloneError, parse_github_url
from doc_schema.models import GeneratedDoc
from renderer.markdown_renderer import attach_search_index
from skeleton_schema.models import RepoSkeleton

router = APIRouter()


def _public_job(job: dict) -> dict:
    has_doc = False
    try:
        has_doc = doc_path(job["id"]).exists()
    except FileNotFoundError:
        has_doc = False
    return {
        "id": job["id"],
        "user_id": job["user_id"],
        "repo_id": job["repo_id"],
        "repo_url": job["repo_url"],
        "status": job["status"],
        "error": job.get("error"),
        "model": job.get("model"),
        "project_type": job.get("project_type"),
        "estimate": job.get("estimate"),
        "progress": job.get("progress"),
        "tokens_used": job.get("tokens_used") or 0,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "has_doc": has_doc,
    }


@router.post("/jobs")
async def submit_job(payload: SubmitJobRequest, user: dict = Depends(get_current_user)):
    try:
        parsed = parse_github_url(payload.repo_url)
    except CloneError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repo = store.upsert_repo(
        user["id"],
        full_name=f"{parsed.owner}/{parsed.name}",
        default_url=f"https://github.com/{parsed.owner}/{parsed.name}",
        visibility="unknown",
    )
    job = await start_job_for_repo(user, repo)
    return _public_job(job)


@router.get("/jobs")
async def jobs(user: dict = Depends(get_current_user)):
    return [_public_job(job) for job in store.list_jobs(user["id"])]


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str, user: dict = Depends(get_current_user)):
    job = store.get_job_for_user(user["id"], job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job(job)


@router.post("/jobs/{job_id}/confirm")
async def confirm_job(job_id: str, payload: ConfirmJobRequest, user: dict = Depends(get_current_user)):
    job = store.get_job_for_user(user["id"], job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in {"awaiting_confirmation", "failed"}:
        raise HTTPException(status_code=409, detail="Job is not waiting for confirmation")
    if job["status"] == "failed" and not skeleton_path(job_id).exists():
        raise HTTPException(status_code=409, detail="Analysis did not complete; submit the repo again")

    settings_row = store.get_settings(user["id"])
    if not settings_row.get("groq_key_encrypted"):
        raise HTTPException(status_code=400, detail="Add a Groq API key in Settings first")

    model = payload.model or job.get("model") or settings_row["default_model"]
    try:
        get_model(model)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    skeleton = RepoSkeleton.model_validate_json(skeleton_path(job_id).read_text(encoding="utf-8"))
    estimate = estimate_job(skeleton, model)
    cap = int(settings_row["max_tokens"])
    if estimate["estimated_input_tokens"] + estimate["estimated_output_tokens"] > cap:
        raise HTTPException(
            status_code=400,
            detail=f"Estimate exceeds the {cap} token cap. Raise the cap in Settings or pick a smaller repo.",
        )

    store.update_job(job_id, model=model, estimate=estimate, status="queued_generation")
    await enqueue_generate(job_id)
    job = store.get_job(job_id)
    return _public_job(job)  # type: ignore[arg-type]


@router.get("/jobs/{job_id}/doc")
async def job_doc(job_id: str, user: dict = Depends(get_current_user)):
    job = store.get_job_for_user(user["id"], job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    path = doc_path(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Documentation is not ready")
    doc = GeneratedDoc.model_validate_json(path.read_text(encoding="utf-8"))
    return attach_search_index(doc).model_dump(mode="json")
