from __future__ import annotations

from typing import Any

from doc_schema.models import ProjectType
from skeleton_schema.models import RepoSkeleton

WEB_DEPS = {
    "fastapi",
    "flask",
    "django",
    "starlette",
    "express",
    "next",
    "koa",
    "hapi",
    "nestjs",
    "gin-gonic/gin",
    "labstack/echo",
    "actix-web",
    "axum",
    "warp",
    "rocket",
    "react",
    "vue",
    "svelte",
    "next.config",
}

CLI_DEPS = {
    "click",
    "typer",
    "argparse",
    "commander",
    "yargs",
    "oclif",
    "cobra",
    "clap",
    "structopt",
    "argh",
}

SERVICE_HINTS = {"dockerfile", "docker-compose", "uvicorn", "gunicorn", "grpc"}


def _flatten_manifest_text(manifests: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key, value in manifests.items():
        chunks.append(key.lower())
        if isinstance(value, str):
            chunks.append(value.lower())
        else:
            chunks.append(str(value).lower())
    return "\n".join(chunks)


def _import_blob(skeleton: RepoSkeleton) -> str:
    parts: list[str] = []
    for file in skeleton.files:
        for item in file.imports:
            parts.append(item.module.lower())
            parts.append(item.raw.lower())
    return "\n".join(parts)


def classify(skeleton: RepoSkeleton) -> tuple[ProjectType, dict[str, Any]]:
    manifest_text = _flatten_manifest_text(skeleton.manifests)
    imports = _import_blob(skeleton)
    blob = f"{manifest_text}\n{imports}"

    cli_score = 0
    web_score = 0
    lib_score = 0
    service_score = 0
    reasons: list[str] = []

    for name, data in skeleton.manifests.items():
        lower = name.lower()
        if lower.endswith("package.json") and isinstance(data, dict):
            if data.get("bin"):
                cli_score += 4
                reasons.append("package.json bin field")
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            dep_names = " ".join(deps.keys()).lower()
            if any(k in dep_names for k in ("express", "next", "koa", "fastify", "nest")):
                web_score += 4
                reasons.append("JS/TS web framework dependency")
            if "next" in dep_names or "react-scripts" in dep_names:
                web_score += 2
            if data.get("bin") is None and data.get("main") and not any(
                k in dep_names for k in ("express", "next", "koa")
            ):
                lib_score += 2
                reasons.append("package.json looks like a published library")
        if lower.endswith("pyproject.toml") and isinstance(data, dict):
            project = data.get("project") or {}
            scripts = project.get("scripts") or {}
            if scripts:
                cli_score += 4
                reasons.append("Python console scripts")
            poetry_scripts = (data.get("tool") or {}).get("poetry", {}).get("scripts") or {}
            if poetry_scripts:
                cli_score += 3
        if lower.endswith("cargo.toml") and isinstance(data, dict):
            bins = data.get("bin")
            if bins:
                cli_score += 3
                reasons.append("Cargo [[bin]]")
            deps = data.get("dependencies") or {}
            dep_text = str(deps).lower()
            if "clap" in dep_text or "structopt" in dep_text:
                cli_score += 3
                reasons.append("Rust CLI parser crate")
            if "actix-web" in dep_text or "axum" in dep_text or "warp" in dep_text or "rocket" in dep_text:
                web_score += 4
                reasons.append("Rust web framework crate")
        if "dockerfile" in lower:
            service_score += 2
            reasons.append("Dockerfile present")

    for dep in CLI_DEPS:
        if dep in blob:
            cli_score += 2
    for dep in WEB_DEPS:
        if dep in blob:
            web_score += 2
    for dep in SERVICE_HINTS:
        if dep in blob:
            service_score += 1

    if skeleton.entry_points:
        if any(p.endswith("main.go") or p.endswith("main.rs") or p.endswith("__main__.py") for p in skeleton.entry_points):
            if web_score < 3:
                cli_score += 1
    else:
        exported = sum(1 for f in skeleton.files for s in f.symbols if s.exported)
        if exported >= 5:
            lib_score += 3
            reasons.append("No entry point with a public API surface")

    scores = {
        ProjectType.cli: cli_score,
        ProjectType.web_app: web_score,
        ProjectType.service: service_score + (2 if web_score >= 3 and "dockerfile" in blob else 0),
        ProjectType.library: lib_score,
    }

    if web_score >= 3 and service_score >= 2 and cli_score < web_score:
        # Backend-looking web with containerization is a service.
        if "react" not in blob and "next" not in blob and "vue" not in blob:
            project_type = ProjectType.service
        else:
            project_type = ProjectType.web_app
    else:
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        best_type, best_score = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0
        if best_score == 0 or (best_score < 3 and best_score - second < 2):
            project_type = ProjectType.general
        else:
            project_type = best_type

    signals = {
        "scores": {k.value: v for k, v in scores.items()},
        "reasons": reasons,
        "project_type": project_type.value,
    }
    return project_type, signals
