from __future__ import annotations

import json

from doc_schema.agents import SurfaceDraft
from doc_schema.models import ProjectType
from skeleton_schema.models import RepoSkeleton

from generation.groq_client import GroqClient
from generation.jsonutil import extract_json
from generation.templates import section_plan

SYSTEM = """You write a surface draft (API reference, CLI commands, or HTTP endpoints).
Return JSON:
{
  "section_type": "api_reference|commands_reference|api_endpoints|usage_examples",
  "title": string,
  "content": "markdown",
  "items": [object],
  "citations": [{"path": string, "line": number}]
}
Use only public_api and manifests. Do not invent symbols.
"""


async def run_surface(
    client: GroqClient,
    skeleton: RepoSkeleton,
    project_type: ProjectType,
) -> SurfaceDraft:
    user = {
        "project_type": project_type.value,
        "section_plan": section_plan(project_type),
        "public_api": [entry.model_dump() for entry in skeleton.public_api[:80]],
        "manifest_keys": list(skeleton.manifests.keys()),
        "manifest_summary": skeleton.manifest_summary,
    }
    try:
        text = await client.complete(
            system=SYSTEM,
            user=json.dumps(user, default=str)[:80_000],
            json_mode=True,
            max_completion_tokens=1200,
        )
        return SurfaceDraft.model_validate(extract_json(text))
    except Exception:
        return SurfaceDraft()
