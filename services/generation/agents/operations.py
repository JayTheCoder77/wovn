from __future__ import annotations

import json

from doc_schema.agents import OperationsDraft
from skeleton_schema.models import RepoSkeleton

from generation.llm import LLMClient
from generation.jsonutil import extract_json

SYSTEM = """You write an operations draft for install, run, and deploy.
Return JSON:
{
  "getting_started": "markdown",
  "env_var_names": ["NAME_ONLY"],
  "notes": ["short strings"],
  "citations": [{"path": string, "line": number}]
}
Use Docker/compose/manifests only. Env values must be names, never secrets.
"""


async def run_operations(client: LLMClient, skeleton: RepoSkeleton) -> OperationsDraft:
    user = {
        "manifest_keys": list(skeleton.manifests.keys()),
        "manifest_summary": skeleton.manifest_summary,
        "readme_digest": skeleton.readme_digest,
    }
    try:
        text = await client.complete(
            system=SYSTEM,
            user=json.dumps(user, default=str)[:80_000],
            json_mode=True,
            max_completion_tokens=900,
        )
        return OperationsDraft.model_validate(extract_json(text))
    except Exception:
        return OperationsDraft()
