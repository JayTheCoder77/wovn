"""Alembic env for Wovn API."""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import context

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps"))
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT / "packages/skeleton-schema"))
sys.path.insert(0, str(ROOT / "packages/doc-schema"))

from api.db import database_url, get_engine
from api.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", database_url())
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
