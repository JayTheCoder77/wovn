from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    settings: Mapped[UserSettings | None] = relationship(back_populates="user")
    github_token: Mapped[GitHubToken | None] = relationship(back_populates="user")
    repos: Mapped[list[Repo]] = relationship(back_populates="user")
    jobs: Mapped[list[DocJob]] = relationship(back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    groq_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    openrouter_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_id: Mapped[str] = mapped_column(String(32), nullable=False, default="fernet-v1")
    llm_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="groq")
    default_model: Mapped[str] = mapped_column(String(200), nullable=False)
    openrouter_default_model: Mapped[str] = mapped_column(String(200), nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="settings")


class GitHubToken(Base):
    __tablename__ = "github_tokens"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    access_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    key_id: Mapped[str] = mapped_column(String(32), nullable=False, default="fernet-v1")

    user: Mapped[User] = relationship(back_populates="github_token")


class Repo(Base):
    __tablename__ = "repos"
    __table_args__ = (UniqueConstraint("user_id", "provider", "full_name", name="uq_repos_user_provider_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="github")
    full_name: Mapped[str] = mapped_column(String(400), nullable=False)
    default_url: Mapped[str] = mapped_column(String(500), nullable=False)
    default_branch: Mapped[str | None] = mapped_column(String(200), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="repos")
    jobs: Mapped[list[DocJob]] = relationship(back_populates="repo")


class DocJob(Base):
    __tablename__ = "doc_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    repo_id: Mapped[str] = mapped_column(String(36), ForeignKey("repos.id"), nullable=False)
    repo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    project_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estimate_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="jobs")
    repo: Mapped[Repo] = relationship(back_populates="jobs")
