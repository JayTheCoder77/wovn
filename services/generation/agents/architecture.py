from __future__ import annotations

import json

from doc_schema.agents import ArchitectureDraft
from skeleton_schema.models import RepoSkeleton

from generation.context.packs import ContextPacks, render_global_pack
from generation.groq_client import GroqClient
from generation.jsonutil import extract_json

SYSTEM = """You write an architecture draft from a global ContextPack and import graph.
Return JSON:
{
  "narrative": "markdown",
  "components": [{"name": string, "role": string}],
  "diagram": "mermaid flowchart or null",
  "citations": [{"path": string, "line": number}]
}
Do not invent files. Cite pack provenance.
"""


async def run_architecture(
    client: GroqClient,
    skeleton: RepoSkeleton,
    packs: ContextPacks,
) -> ArchitectureDraft:
    user = {
        "global_pack": render_global_pack(packs.global_pack),
        "import_graph": skeleton.import_graph,
        "entry_points": skeleton.entry_points,
        "languages": [lang.value for lang in skeleton.languages],
    }
    try:
        text = await client.complete(
            system=SYSTEM,
            user=json.dumps(user, default=str)[:80_000],
            json_mode=True,
            max_completion_tokens=1200,
        )
        return ArchitectureDraft.model_validate(extract_json(text))
    except Exception:
        return ArchitectureDraft()
