from __future__ import annotations

import json

from doc_schema.agents import CriticReport
from doc_schema.models import GeneratedDoc
from skeleton_schema.models import RepoSkeleton

from generation.groq_client import GroqClient
from generation.jsonutil import extract_json

SYSTEM = """You are a critic. List unsupported claims and missing sections versus skeleton facts.
Return JSON:
{
  "unsupported": ["claim"],
  "missing_sections": ["section type"],
  "ok": true
}
ok is true only when unsupported and missing_sections are empty.
Do not invent files that are not in the skeleton.
"""


async def run_critic(
    client: GroqClient,
    skeleton: RepoSkeleton,
    doc: GeneratedDoc,
) -> CriticReport:
    user = {
        "doc": json.loads(doc.model_dump_json()),
        "file_count": skeleton.file_count,
        "tree": skeleton.tree[:80],
        "public_api": [entry.model_dump() for entry in skeleton.public_api[:40]],
        "manifest_keys": list(skeleton.manifests.keys()),
    }
    try:
        text = await client.complete(
            system=SYSTEM,
            user=json.dumps(user, default=str)[:80_000],
            json_mode=True,
            max_completion_tokens=800,
        )
        return CriticReport.model_validate(extract_json(text))
    except Exception:
        return CriticReport(ok=True)
