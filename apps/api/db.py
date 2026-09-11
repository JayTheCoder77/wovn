from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.config import settings


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> Path:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings.data_dir / "wovn.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                groq_key_encrypted TEXT,
                default_model TEXT NOT NULL,
                max_tokens INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                repo_url TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                model TEXT,
                project_type TEXT,
                estimate_json TEXT,
                progress_json TEXT,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        row = conn.execute("SELECT id FROM settings WHERE id = 1").fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO settings (id, groq_key_encrypted, default_model, max_tokens, updated_at)
                VALUES (1, NULL, 'openai/gpt-oss-20b', ?, ?)
                """,
                (settings.max_tokens_default, utcnow()),
            )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in ("estimate_json", "progress_json"):
        if key in data and data[key]:
            data[key.replace("_json", "")] = json.loads(data[key])
        elif key in data:
            data[key.replace("_json", "")] = None
    return data
