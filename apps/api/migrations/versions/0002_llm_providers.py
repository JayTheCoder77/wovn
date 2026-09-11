"""add OpenRouter settings and job provider

Revision ID: 0002_llm_providers
Revises: 0001_phase_a
Create Date: 2026-09-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_llm_providers"
down_revision: Union[str, None] = "0001_phase_a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("openrouter_key_encrypted", sa.Text(), nullable=True))
    op.add_column("user_settings", sa.Column("llm_provider", sa.String(length=32), nullable=False, server_default="groq"))
    op.add_column(
        "user_settings",
        sa.Column("openrouter_default_model", sa.String(length=200), nullable=False, server_default="openai/gpt-4o-mini"),
    )
    op.add_column("doc_jobs", sa.Column("llm_provider", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("doc_jobs", "llm_provider")
    op.drop_column("user_settings", "openrouter_default_model")
    op.drop_column("user_settings", "llm_provider")
    op.drop_column("user_settings", "openrouter_key_encrypted")
