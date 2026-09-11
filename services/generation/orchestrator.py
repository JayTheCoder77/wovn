from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from doc_schema.agents import (
    ArchitectureDraft,
    CriticReport,
    OperationsDraft,
    RunPlan,
    SurfaceDraft,
)
from doc_schema.models import GeneratedDoc, ProjectType
from skeleton_schema.models import RepoSkeleton

from generation.agents.architecture import run_architecture
from generation.agents.coordinator import coordinate
from generation.agents.critic import run_critic
from generation.agents.operations import run_operations
from generation.agents.surface import run_surface
from generation.context.packs import ContextPacks, ModulePack
from generation.groq_client import GroqClient
from generation.summarize import summarize_all
from generation.synthesize import synthesize

Progress = Callable[[str], Awaitable[None]] | None


async def run_multi_agent(
    client: GroqClient,
    skeleton: RepoSkeleton,
    packs: ContextPacks,
    project_type: ProjectType,
    *,
    artifact_dir: Path,
    on_progress: Progress = None,
) -> GeneratedDoc:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if on_progress:
        await on_progress("Planning run")
    plan = await coordinate(client, skeleton, packs, project_type)
    _write_json(artifact_dir / "coordinator.json", plan.model_dump())

    selected = _selected_modules(packs, plan)
    drafts: dict[str, ArchitectureDraft | SurfaceDraft | OperationsDraft | None] = {
        "architecture": None,
        "surface": None,
        "operations": None,
    }

    async def summaries_task() -> list[dict]:
        return await summarize_all(client, selected, on_progress=on_progress)

    async def architecture_task() -> ArchitectureDraft | None:
        if not plan.run_architecture:
            return None
        if on_progress:
            await on_progress("Analyzing architecture")
        draft = await run_architecture(client, skeleton, packs)
        _write_json(artifact_dir / "architecture.json", draft.model_dump())
        return draft

    async def surface_task() -> SurfaceDraft | None:
        if not plan.run_surface:
            return None
        if on_progress:
            await on_progress("Analyzing surface")
        draft = await run_surface(client, skeleton, project_type)
        _write_json(artifact_dir / "surface.json", draft.model_dump())
        return draft

    async def operations_task() -> OperationsDraft | None:
        if not plan.run_operations:
            return None
        if on_progress:
            await on_progress("Analyzing operations")
        draft = await run_operations(client, skeleton)
        _write_json(artifact_dir / "operations.json", draft.model_dump())
        return draft

    summaries, drafts["architecture"], drafts["surface"], drafts["operations"] = await asyncio.gather(
        summaries_task(), architecture_task(), surface_task(), operations_task()
    )

    if on_progress:
        await on_progress("Synthesizing documentation")
    doc = await synthesize(
        client,
        skeleton,
        project_type,
        summaries,
        packs=packs,
        drafts={
            "architecture": drafts["architecture"],
            "surface": drafts["surface"],
            "operations": drafts["operations"],
        },
    )

    if plan.run_critic:
        if on_progress:
            await on_progress("Reviewing draft")
        critic = await run_critic(client, skeleton, doc)
        _write_json(artifact_dir / "critic.json", critic.model_dump())
        if not critic.ok:
            if on_progress:
                await on_progress("Repairing documentation")
            doc = await synthesize(
                client,
                skeleton,
                project_type,
                summaries,
                packs=packs,
                drafts={
                    "architecture": drafts["architecture"],
                    "surface": drafts["surface"],
                    "operations": drafts["operations"],
                },
                critic=critic,
            )
    return doc


def _selected_modules(packs: ContextPacks, plan: RunPlan) -> list[ModulePack]:
    wanted = set(plan.module_names)
    selected = [module for module in packs.modules if module.name in wanted]
    return selected or list(packs.modules)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
