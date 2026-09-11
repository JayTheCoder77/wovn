from __future__ import annotations

import asyncio

from generation.groq_client import GroqClient
from generation.jsonutil import extract_json
from generation.modules import ModuleGroup, file_context

SYSTEM = """You summarize source modules from a static-analysis skeleton, not raw source.
Return JSON with keys:
- purpose: one paragraph
- key_exports: array of {name, signature, summary}
- dependencies: array of strings
- notable_patterns: array of short strings
Be precise. Do not invent files, functions, or frameworks that are not in the skeleton.
"""


async def summarize_group(client: GroqClient, group: ModuleGroup) -> dict:
    body = "\n".join(file_context(f) for f in group.files)
    user = f"Module: {group.name}\n\n{body}"
    text = await client.complete(system=SYSTEM, user=user, json_mode=True, max_completion_tokens=900)
    data = extract_json(text)
    data["module"] = group.name
    data["files"] = [f.path for f in group.files]
    return data


async def summarize_all(
    client: GroqClient,
    groups: list[ModuleGroup],
    on_progress=None,
    concurrency: int = 4,
) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict | None] = [None] * len(groups)

    async def run(index: int, group: ModuleGroup) -> None:
        async with semaphore:
            if on_progress:
                await on_progress(
                    f"Analyzing module {index + 1}/{len(groups)} ({group.name})"
                )
            try:
                results[index] = await summarize_group(client, group)
            except Exception as exc:
                results[index] = {
                    "module": group.name,
                    "files": [f.path for f in group.files],
                    "purpose": f"Summary unavailable: {exc}",
                    "key_exports": [],
                    "dependencies": [],
                    "notable_patterns": [],
                }

    await asyncio.gather(*(run(i, g) for i, g in enumerate(groups)))
    return [item for item in results if item is not None]
