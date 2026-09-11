from __future__ import annotations

from pathlib import Path

from api.config import settings
from api.jobs import store


def job_dir_for(job: dict) -> Path:
    path = settings.data_dir / job["user_id"] / job["repo_id"] / job["id"]
    path.mkdir(parents=True, exist_ok=True)
    return path


def job_dir(job_id: str) -> Path:
    job = store.get_job(job_id)
    if job is None:
        raise FileNotFoundError(job_id)
    return job_dir_for(job)


def skeleton_path(job_id: str) -> Path:
    return job_dir(job_id) / "skeleton.json"


def doc_path(job_id: str) -> Path:
    return job_dir(job_id) / "doc.json"
