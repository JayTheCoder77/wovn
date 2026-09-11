from __future__ import annotations

import asyncio

from generation.context.packs import ModulePack, render_module_pack
from generation.groq_client import GroqClient
from generation.jsonutil import extract_json

SYSTEM = """You summarize source modules from a static-analysis ContextPack, not whole files.
Return JSON with keys:
- purpose: one paragraph
- key_exports: array of {name, signature, summary}
- dependencies: array of strings
- notable_patterns: array of short strings
- citations: array of {path, line} referring to FILE/SNIPPET provenance in the pack
Be precise. Do not invent files, functions, or frameworks that are not in the pack.
Every claim should cite a path and line from the pack.
"""


async def summarize_group(client: GroqClient, group: ModulePack) -> dict:
    body = render_module_pack(group)
    user = f"Module: {group.name}\n\n{body}"
    text = await client.complete(system=SYSTEM, user=user, json_mode=True, max_completion_tokens=900)
    data = extract_json(text)
    data["module"] = group.name
    data["files"] = [f.path for f in group.files]
    data.setdefault("citations", [])
    return data


async def summarize_all(
    client: GroqClient,
    groups: list[ModulePack],
    on_progress=None,
    concurrency: int = 4,
) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict | None] = [None] * len(groups)

    async def run(index: int, group: ModulePack) -> None:
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
