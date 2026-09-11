from __future__ import annotations

import json

from doc_schema.agents import RunPlan
from doc_schema.models import ProjectType
from skeleton_schema.models import RepoSkeleton

from generation.context.packs import ContextPacks, render_global_pack
from generation.llm import LLMClient
from generation.jsonutil import extract_json
from generation.templates import section_plan

SYSTEM = """You choose which modules and specialist agents to run for a documentation run plan.
Return JSON:
{
  "module_names": ["existing module names only"],
  "run_architecture": true,
  "run_surface": true,
  "run_operations": true,
  "run_critic": false,
  "rationale": "short"
}
Rules:
- Do not invent files or modules. Only use names from the provided module list.
- Skip Surface when there is no public API and project_type is general.
- Skip Operations when there are no manifests.
- Prefer run_critic true when file_count > 20; you may override.
"""


def fallback_plan(available: list[str], file_count: int) -> RunPlan:
    return RunPlan(
        module_names=list(available),
        run_architecture=True,
        run_surface=True,
        run_operations=True,
        run_critic=file_count > 20,
        rationale="fallback",
    )


def clamp_plan(plan: RunPlan, available: list[str]) -> RunPlan:
    allowed = set(available)
    names = [name for name in plan.module_names if name in allowed]
    if not names:
        names = list(available)
    return plan.model_copy(update={"module_names": names})


async def coordinate(
    client: LLMClient,
    skeleton: RepoSkeleton,
    packs: ContextPacks,
    project_type: ProjectType,
) -> RunPlan:
    available = [module.name for module in packs.modules]
    payload = {
        "project_type": project_type.value,
        "section_plan": section_plan(project_type),
        "file_count": skeleton.file_count,
        "module_names": available,
        "public_api": [entry.name for entry in skeleton.public_api[:40]],
        "manifest_keys": list(skeleton.manifests.keys()),
        "global_pack": render_global_pack(packs.global_pack)[:4000],
    }
    try:
        text = await client.complete(
            system=SYSTEM,
            user=json.dumps(payload, default=str),
            json_mode=True,
            max_completion_tokens=400,
        )
        plan = RunPlan.model_validate(extract_json(text))
        return clamp_plan(plan, available)
    except Exception:
        return fallback_plan(available, skeleton.file_count)
