from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth.keys import FERNET_KEY_ID, encrypt_key
from api.config import settings
from api.db import SessionLocal
from api.models import DocJob, GitHubToken, Repo, User, UserSettings
from estimator.pricing import DEFAULT_MODELS, DEFAULT_MODEL
from generation.llm import LLMProvider


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _user_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "github_id": int(user.github_id),
        "email": user.email,
        "display_name": user.display_name,
        "created_at": _iso(user.created_at),
    }


def _settings_dict(row: UserSettings) -> dict[str, Any]:
    return {
        "user_id": row.user_id,
        "groq_key_encrypted": row.groq_key_encrypted,
        "openrouter_key_encrypted": row.openrouter_key_encrypted,
        "key_id": row.key_id,
        "llm_provider": row.llm_provider,
        "default_model": row.default_model,
        "openrouter_default_model": row.openrouter_default_model,
        "max_tokens": row.max_tokens,
        "updated_at": _iso(row.updated_at),
    }


def _repo_dict(repo: Repo) -> dict[str, Any]:
    return {
        "id": repo.id,
        "user_id": repo.user_id,
        "provider": repo.provider,
        "full_name": repo.full_name,
        "default_url": repo.default_url,
        "default_branch": repo.default_branch,
        "visibility": repo.visibility,
        "last_analyzed_at": _iso(repo.last_analyzed_at),
    }


def _job_dict(job: DocJob) -> dict[str, Any]:
    estimate = json.loads(job.estimate_json) if job.estimate_json else None
    progress = json.loads(job.progress_json) if job.progress_json else None
    return {
        "id": job.id,
        "user_id": job.user_id,
        "repo_id": job.repo_id,
        "repo_url": job.repo_url,
        "status": job.status,
        "error": job.error,
        "model": job.model,
        "llm_provider": job.llm_provider,
        "project_type": job.project_type,
        "estimate": estimate,
        "progress": progress,
        "tokens_used": job.tokens_used,
        "created_at": _iso(job.created_at),
        "updated_at": _iso(job.updated_at),
    }


def _ensure_settings(session: Session, user_id: str) -> UserSettings:
    row = session.get(UserSettings, user_id)
    if row is None:
        row = UserSettings(
            user_id=user_id,
            groq_key_encrypted=None,
            openrouter_key_encrypted=None,
            key_id=FERNET_KEY_ID,
            default_model=DEFAULT_MODEL,
            openrouter_default_model=DEFAULT_MODELS[LLMProvider.OPENROUTER],
            llm_provider=LLMProvider.GROQ.value,
            max_tokens=settings.max_tokens_default,
            updated_at=utcnow(),
        )
        session.add(row)
        session.flush()
    return row


def upsert_github_user(
    *,
    github_id: int,
    email: str | None,
    display_name: str,
    access_token: str,
    refresh_token: str | None,
    expires_at: datetime | None,
) -> dict[str, Any]:
    with session_scope() as session:
        user = session.scalar(select(User).where(User.github_id == github_id))
        if user is None:
            user = User(
                id=str(uuid.uuid4()),
                github_id=github_id,
                email=email,
                display_name=display_name,
                created_at=utcnow(),
            )
            session.add(user)
            session.flush()
        else:
            user.email = email or user.email
            user.display_name = display_name
        _ensure_settings(session, user.id)
        token = session.get(GitHubToken, user.id)
        if token is None:
            token = GitHubToken(user_id=user.id, access_encrypted="", key_id=FERNET_KEY_ID)
            session.add(token)
        token.access_encrypted = encrypt_key(access_token)
        token.refresh_encrypted = encrypt_key(refresh_token) if refresh_token else None
        token.expires_at = expires_at
        token.key_id = FERNET_KEY_ID
        session.flush()
        return _user_dict(user)


def get_user(user_id: str) -> dict[str, Any] | None:
    with session_scope() as session:
        user = session.get(User, user_id)
        return _user_dict(user) if user else None


def get_settings(user_id: str) -> dict[str, Any]:
    with session_scope() as session:
        row = _ensure_settings(session, user_id)
        return _settings_dict(row)


def update_settings(user_id: str, **fields: Any) -> dict[str, Any]:
    with session_scope() as session:
        row = _ensure_settings(session, user_id)
        for key, value in fields.items():
            setattr(row, key, value)
        if any(fields.get(name) for name in ("groq_key_encrypted", "openrouter_key_encrypted")):
            row.key_id = FERNET_KEY_ID
        row.updated_at = utcnow()
        session.flush()
        return _settings_dict(row)


def get_github_token(user_id: str) -> dict[str, Any] | None:
    with session_scope() as session:
        row = session.get(GitHubToken, user_id)
        if row is None:
            return None
        return {
            "user_id": row.user_id,
            "access_encrypted": row.access_encrypted,
            "refresh_encrypted": row.refresh_encrypted,
            "expires_at": row.expires_at,
            "key_id": row.key_id,
        }


def upsert_github_tokens(
    user_id: str,
    *,
    access_token: str,
    refresh_token: str | None,
    expires_at: datetime | None,
) -> None:
    with session_scope() as session:
        token = session.get(GitHubToken, user_id)
        if token is None:
            token = GitHubToken(user_id=user_id, access_encrypted="", key_id=FERNET_KEY_ID)
            session.add(token)
        token.access_encrypted = encrypt_key(access_token)
        token.refresh_encrypted = encrypt_key(refresh_token) if refresh_token else None
        token.expires_at = expires_at
        token.key_id = FERNET_KEY_ID


def upsert_repo(
    user_id: str,
    *,
    full_name: str,
    default_url: str,
    visibility: str = "unknown",
    default_branch: str | None = None,
    provider: str = "github",
) -> dict[str, Any]:
    with session_scope() as session:
        repo = session.scalar(
            select(Repo).where(
                Repo.user_id == user_id,
                Repo.provider == provider,
                Repo.full_name == full_name,
            )
        )
        if repo is None:
            repo = Repo(
                id=str(uuid.uuid4()),
                user_id=user_id,
                provider=provider,
                full_name=full_name,
                default_url=default_url,
                default_branch=default_branch,
                visibility=visibility,
            )
            session.add(repo)
        else:
            repo.default_url = default_url
            repo.visibility = visibility
            if default_branch:
                repo.default_branch = default_branch
        session.flush()
        return _repo_dict(repo)


def list_repos(user_id: str) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(select(Repo).where(Repo.user_id == user_id).order_by(Repo.full_name)).all()
        return [_repo_dict(row) for row in rows]


def get_repo(user_id: str, repo_id: str) -> dict[str, Any] | None:
    with session_scope() as session:
        repo = session.get(Repo, repo_id)
        if repo is None or repo.user_id != user_id:
            return None
        return _repo_dict(repo)


def touch_repo_analyzed(repo_id: str) -> None:
    with session_scope() as session:
        repo = session.get(Repo, repo_id)
        if repo is not None:
            repo.last_analyzed_at = utcnow()


def list_jobs(user_id: str, limit: int = 30) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(
            select(DocJob).where(DocJob.user_id == user_id).order_by(DocJob.created_at.desc()).limit(limit)
        ).all()
        return [_job_dict(row) for row in rows]


def get_job(job_id: str) -> dict[str, Any] | None:
    with session_scope() as session:
        job = session.get(DocJob, job_id)
        return _job_dict(job) if job else None


def get_job_for_user(user_id: str, job_id: str) -> dict[str, Any] | None:
    job = get_job(job_id)
    if job is None or job["user_id"] != user_id:
        return None
    return job


def create_job(job_id: str, user_id: str, repo_id: str, repo_url: str) -> dict[str, Any]:
    now = utcnow()
    with session_scope() as session:
        job = DocJob(
            id=job_id,
            user_id=user_id,
            repo_id=repo_id,
            repo_url=repo_url,
            status="queued",
            error=None,
            model=None,
            llm_provider=None,
            project_type=None,
            estimate_json=None,
            progress_json=json.dumps({"stage": "queued", "message": "Queued"}),
            tokens_used=0,
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        session.flush()
        return _job_dict(job)


def update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    payload = dict(fields)
    if "estimate" in payload:
        payload["estimate_json"] = json.dumps(payload.pop("estimate"))
    if "progress" in payload:
        payload["progress_json"] = json.dumps(payload.pop("progress"))
    payload["updated_at"] = utcnow()
    with session_scope() as session:
        job = session.get(DocJob, job_id)
        if job is None:
            return
        for key, value in payload.items():
            setattr(job, key, value)
