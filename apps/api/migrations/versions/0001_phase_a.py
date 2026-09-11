"""phase a users repos jobs

Revision ID: 0001_phase_a
Revises:
Create Date: 2026-09-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_phase_a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("groq_key_encrypted", sa.Text(), nullable=True),
        sa.Column("key_id", sa.String(length=32), nullable=False),
        sa.Column("default_model", sa.String(length=200), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "github_tokens",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("access_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_encrypted", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("key_id", sa.String(length=32), nullable=False),
    )
    op.create_table(
        "repos",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=400), nullable=False),
        sa.Column("default_url", sa.String(length=500), nullable=False),
        sa.Column("default_branch", sa.String(length=200), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "provider", "full_name", name="uq_repos_user_provider_name"),
    )
    op.create_table(
        "doc_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("repo_id", sa.String(length=36), sa.ForeignKey("repos.id"), nullable=False),
        sa.Column("repo_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("project_type", sa.String(length=64), nullable=True),
        sa.Column("estimate_json", sa.Text(), nullable=True),
        sa.Column("progress_json", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("doc_jobs")
    op.drop_table("repos")
    op.drop_table("github_tokens")
    op.drop_table("user_settings")
    op.drop_table("users")
