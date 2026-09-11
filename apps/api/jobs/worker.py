from __future__ import annotations

import asyncio
import shutil
import uuid

from analysis.classifier import classify
from analysis.skeleton_builder import build_skeleton
from api.auth.github_api import GitHubAuthError, valid_access_token
from api.auth.keys import decrypt_key
from api.config import settings
from api.jobs import store
from api.jobs.paths import doc_path, job_dir, skeleton_path
from doc_schema.models import ProjectType
from estimator.estimate import estimate_job
from estimator.pricing import DEFAULT_MODEL, get_model
from generation.groq_client import GroqClient
from generation.context.packs import build_context_packs
from generation.summarize import summarize_all
from generation.synthesize import synthesize
from ingest.clone import CloneError, clone_repo
from renderer.diagram_gen import ensure_architecture_diagram, mermaid_from_import_graph
from renderer.markdown_renderer import attach_search_index
from skeleton_schema.models import RepoSkeleton

_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()


def load_skeleton(job_id: str) -> RepoSkeleton:
    return RepoSkeleton.model_validate_json(skeleton_path(job_id).read_text(encoding="utf-8"))


async def enqueue_analyze(job_id: str) -> None:
    await _queue.put((job_id, "analyze"))


async def enqueue_generate(job_id: str) -> None:
    await _queue.put((job_id, "generate"))


async def worker_loop() -> None:
    while True:
        job_id, action = await _queue.get()
        try:
            if action == "analyze":
                await asyncio.to_thread(_analyze_job, job_id)
            elif action == "generate":
                await _generate_job(job_id)
        except Exception as exc:
            store.update_job(
                job_id,
                status="failed",
                error=str(exc),
                progress={"stage": "failed", "message": str(exc)},
            )
        finally:
            _queue.task_done()


def _analyze_job(job_id: str) -> None:
    job = store.get_job(job_id)
    if not job:
        return
    job_dir(job_id)
    clone_dir = settings.data_dir / "clones" / job_id
    store.update_job(
        job_id,
        status="analyzing",
        progress={"stage": "cloning", "message": "Shallow-cloning repository"},
    )
    try:
        try:
            access_token = valid_access_token(job["user_id"])
        except GitHubAuthError as exc:
            raise CloneError(str(exc)) from exc
        parsed = clone_repo(job["repo_url"], clone_dir, access_token=access_token)
        store.update_job(
            job_id,
            progress={"stage": "analyzing", "message": "Building static skeleton"},
        )
        skeleton = build_skeleton(clone_dir, repo_url=job["repo_url"], root_name=parsed.name)
        if skeleton.file_count == 0:
            raise CloneError("No Python, TypeScript, JavaScript, Go, or Rust source files were found.")
        project_type, signals = classify(skeleton)
        skeleton.classifier_signals = signals
        skeleton_path(job_id).write_text(skeleton.model_dump_json(indent=2), encoding="utf-8")
        settings_row = store.get_settings(job["user_id"])
        model = settings_row["default_model"] or DEFAULT_MODEL
        try:
            get_model(model)
        except KeyError:
            model = DEFAULT_MODEL
        estimate = estimate_job(skeleton, model)
        store.update_job(
            job_id,
            status="awaiting_confirmation",
            project_type=project_type.value,
            model=model,
            estimate=estimate,
            progress={
                "stage": "awaiting_confirmation",
                "message": "Static analysis complete. Confirm to generate docs.",
            },
        )
        store.touch_repo_analyzed(job["repo_id"])
    except CloneError as exc:
        store.update_job(
            job_id,
            status="failed",
            error=str(exc),
            progress={"stage": "failed", "message": str(exc)},
        )
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)


async def _generate_job(job_id: str) -> None:
    job = store.get_job(job_id)
    if not job:
        return
    settings_row = store.get_settings(job["user_id"])
    if not settings_row.get("groq_key_encrypted"):
        store.update_job(
            job_id,
            status="awaiting_confirmation",
            error="Add a Groq API key in Settings before generating.",
            progress={"stage": "awaiting_confirmation", "message": "Groq API key required"},
        )
        return

    api_key = decrypt_key(settings_row["groq_key_encrypted"])
    model = job.get("model") or settings_row["default_model"] or DEFAULT_MODEL
    max_tokens = int(settings_row["max_tokens"] or settings.max_tokens_default)
    skeleton = load_skeleton(job_id)
    project_type = ProjectType(job.get("project_type") or "general")
    packs = build_context_packs(skeleton)
    client = GroqClient(api_key=api_key, model=model, max_tokens_remaining=max_tokens)

    async def on_progress(message: str) -> None:
        store.update_job(
            job_id,
            progress={
                "stage": "generating",
                "message": f"{message} — {client.tokens_used} tokens used so far",
                "tokens_used": client.tokens_used,
            },
            tokens_used=client.tokens_used,
        )

    store.update_job(
        job_id,
        status="generating",
        error=None,
        progress={"stage": "generating", "message": "Starting summarization"},
    )
    summaries = await summarize_all(client, packs.modules, on_progress=on_progress)
    await on_progress("Synthesizing documentation")
    doc = await synthesize(client, skeleton, project_type, summaries, packs=packs)
    mermaid = mermaid_from_import_graph(skeleton.import_graph)
    doc = ensure_architecture_diagram(doc, mermaid)
    doc = attach_search_index(doc)
    doc_path(job_id).write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    store.update_job(
        job_id,
        status="completed",
        tokens_used=client.tokens_used,
        progress={
            "stage": "completed",
            "message": "Documentation ready",
            "tokens_used": client.tokens_used,
        },
    )


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]
