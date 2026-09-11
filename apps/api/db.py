from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from api.config import settings

_engine: Engine | None = None
_engine_url: str | None = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


def database_url() -> str:
    if settings.database_url:
        return settings.database_url
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    path = (settings.data_dir / "wovn.db").resolve()
    return f"sqlite:///{path}"


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_engine() -> Engine:
    global _engine, _engine_url
    url = database_url()
    if _engine is None or _engine_url != url:
        if _engine is not None:
            _engine.dispose()
        _engine = create_engine(url, future=True, connect_args=_connect_args(url))
        _engine_url = url
        SessionLocal.configure(bind=_engine)
    return _engine


def reset_engine() -> None:
    global _engine, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None


def alembic_config() -> Config:
    migrations = Path(__file__).resolve().parent / "migrations"
    cfg = Config()
    cfg.set_main_option("script_location", str(migrations))
    cfg.set_main_option("sqlalchemy.url", database_url())
    return cfg


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    get_engine()
    command.upgrade(alembic_config(), "head")
