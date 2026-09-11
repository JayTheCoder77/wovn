from __future__ import annotations

import json
from typing import Any

from api.db import connect, row_to_dict, utcnow


def list_jobs(limit: int = 30) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]  # type: ignore[misc]


def get_job(job_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_dict(row)


def create_job(job_id: str, repo_url: str) -> dict[str, Any]:
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, repo_url, status, error, model, project_type, estimate_json, progress_json, tokens_used, created_at, updated_at)
            VALUES (?, ?, 'queued', NULL, NULL, NULL, NULL, ?, 0, ?, ?)
            """,
            (job_id, repo_url, json.dumps({"stage": "queued", "message": "Queued"}), now, now),
        )
    job = get_job(job_id)
    assert job is not None
    return job


def update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    payload = dict(fields)
    if "estimate" in payload:
        payload["estimate_json"] = json.dumps(payload.pop("estimate"))
    if "progress" in payload:
        payload["progress_json"] = json.dumps(payload.pop("progress"))
    payload["updated_at"] = utcnow()
    assignments = ", ".join(f"{key} = ?" for key in payload)
    values = list(payload.values()) + [job_id]
    with connect() as conn:
        conn.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", values)


def get_settings() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    assert row is not None
    return dict(row)


def update_settings(**fields: Any) -> dict[str, Any]:
    payload = dict(fields)
    payload["updated_at"] = utcnow()
    assignments = ", ".join(f"{key} = ?" for key in payload)
    values = list(payload.values())
    with connect() as conn:
        conn.execute(f"UPDATE settings SET {assignments} WHERE id = 1", values)
    return get_settings()
