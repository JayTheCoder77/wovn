from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.jobs import store
from api.jobs.worker import enqueue_analyze, enqueue_generate, new_job_id
from api.routes.schemas import ConfirmJobRequest, SubmitJobRequest
from estimator.pricing import get_model
from ingest.clone import CloneError, parse_github_url
from doc_schema.models import GeneratedDoc
from renderer.markdown_renderer import attach_search_index
from api.config import settings

router = APIRouter()


def _public_job(job: dict) -> dict:
    return {
        "id": job["id"],
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
        "has_doc": (settings.data_dir / "jobs" / job["id"] / "doc.json").exists(),
    }


@router.post("/jobs")
async def submit_job(payload: SubmitJobRequest):
    try:
        parse_github_url(payload.repo_url)
    except CloneError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job_id = new_job_id()
    job = store.create_job(job_id, payload.repo_url.strip())
    await enqueue_analyze(job_id)
    return _public_job(job)


@router.get("/jobs")
async def jobs():
    return [_public_job(job) for job in store.list_jobs()]


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_job(job)


@router.post("/jobs/{job_id}/confirm")
async def confirm_job(job_id: str, payload: ConfirmJobRequest):
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] not in {"awaiting_confirmation", "failed"}:
        raise HTTPException(status_code=409, detail="Job is not waiting for confirmation")
    if job["status"] == "failed" and not (settings.data_dir / "jobs" / job_id / "skeleton.json").exists():
        raise HTTPException(status_code=409, detail="Analysis did not complete; submit the repo again")

    settings_row = store.get_settings()
    if not settings_row.get("groq_key_encrypted"):
        raise HTTPException(status_code=400, detail="Add a Groq API key in Settings first")

    model = payload.model or job.get("model") or settings_row["default_model"]
    try:
        get_model(model)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    from estimator.estimate import estimate_job
    from skeleton_schema.models import RepoSkeleton

    skeleton = RepoSkeleton.model_validate_json(
        (settings.data_dir / "jobs" / job_id / "skeleton.json").read_text(encoding="utf-8")
    )
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
async def job_doc(job_id: str):
    path = settings.data_dir / "jobs" / job_id / "doc.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Documentation is not ready")
    doc = GeneratedDoc.model_validate_json(path.read_text(encoding="utf-8"))
    return attach_search_index(doc).model_dump(mode="json")
