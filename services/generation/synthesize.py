from __future__ import annotations

from typing import Any

from doc_schema.agents import ArchitectureDraft, CriticReport, OperationsDraft, SurfaceDraft
from doc_schema.models import DocSection, GeneratedDoc, ProjectType, StructureEntry
from skeleton_schema.models import RepoSkeleton

from generation.context.packs import ContextPacks, render_global_pack
from generation.groq_client import GroqClient
from generation.jsonutil import extract_json
from generation.templates import section_plan

SYSTEM = """You merge structured agent drafts and module summaries into documentation. Merge only; no new facts.
Return a JSON object with:
{
  "title": string,
  "overview": string (markdown),
  "getting_started": string (markdown),
  "structure": [{"path": string, "purpose": string}],
  "sections": [
     {"type": string, "title": string, "content": string, "diagram": string|null, "items": object[]}
  ]
}
Rules:
- Only use information present in the global pack, summaries, and drafts.
- Overview must mention detected languages/stack.
- For architecture sections, diagram should be a mermaid flowchart if relationships are known, else null.
- getting_started should derive install commands from manifests or the operations draft when present.
- If critic notes are provided, fix those issues using existing drafts only.
"""


def _fallback(skeleton: RepoSkeleton, project_type: ProjectType, summaries: list[dict]) -> GeneratedDoc:
    structure = [
        StructureEntry(
            path=item.get("module", ""),
            purpose=str(item.get("purpose", ""))[:240],
        )
        for item in summaries
    ]
    overview_bits = [str(item.get("purpose", "")).strip() for item in summaries if item.get("purpose")]
    languages = ", ".join(lang.value for lang in skeleton.languages) or "unknown"
    overview = (
        f"{skeleton.root_name} is a {project_type.value.replace('_', ' ')} "
        f"using {languages}.\n\n" + "\n\n".join(overview_bits[:8])
    )
    getting = _getting_started_from_manifests(skeleton)
    sections = [
        DocSection(
            type="module_breakdown",
            title="Module breakdown",
            content="\n\n".join(
                f"### {item.get('module')}\n{item.get('purpose', '')}" for item in summaries
            ),
        )
    ]
    return GeneratedDoc(
        project_type=project_type,
        title=skeleton.root_name,
        repo_url=skeleton.repo_url,
        overview=overview,
        getting_started=getting,
        structure=structure,
        sections=sections,
    )


def _getting_started_from_manifests(skeleton: RepoSkeleton) -> str:
    names = {k.lower(): v for k, v in skeleton.manifests.items()}
    lines = ["Install from the repository root using the detected toolchain:"]
    if any(k.endswith("package.json") for k in names):
        lines.append("- Node: `npm install` (or `pnpm install`)")
    if any(k.endswith("pyproject.toml") or k.endswith("requirements.txt") for k in names):
        lines.append("- Python: `pip install -e .` or `pip install -r requirements.txt`")
    if any(k.endswith("go.mod") for k in names):
        lines.append("- Go: `go mod download` then `go test ./...`")
    if any(k.endswith("cargo.toml") for k in names):
        lines.append("- Rust: `cargo build`")
    if len(lines) == 1:
        lines.append("- See the repository README for setup details.")
    return "\n".join(lines)


async def synthesize(
    client: GroqClient,
    skeleton: RepoSkeleton,
    project_type: ProjectType,
    summaries: list[dict[str, Any]],
    packs: ContextPacks | None = None,
    drafts: dict[str, ArchitectureDraft | SurfaceDraft | OperationsDraft | None] | None = None,
    critic: CriticReport | None = None,
) -> GeneratedDoc:
    plan = section_plan(project_type)
    global_pack = render_global_pack(packs.global_pack) if packs else ""
    draft_payload = drafts or {}
    user = {
        "repo": skeleton.root_name,
        "repo_url": skeleton.repo_url,
        "project_type": project_type.value,
        "required_section_types": plan,
        "languages": [lang.value for lang in skeleton.languages],
        "entry_points": skeleton.entry_points,
        "global_pack": global_pack,
        "summaries": summaries,
        "signals": skeleton.classifier_signals,
        "architecture": _dump(draft_payload.get("architecture")),
        "surface": _dump(draft_payload.get("surface")),
        "operations": _dump(draft_payload.get("operations")),
        "critic": critic.model_dump() if critic else None,
    }
    import json

    try:
        text = await client.complete(
            system=SYSTEM,
            user=json.dumps(user, default=str)[:120_000],
            json_mode=True,
            max_completion_tokens=4000,
        )
        data = extract_json(text)
        sections = []
        for section in data.get("sections") or []:
            sections.append(
                DocSection(
                    type=str(section.get("type") or "section"),
                    title=str(section.get("title") or "Section"),
                    content=str(section.get("content") or ""),
                    diagram=section.get("diagram"),
                    items=list(section.get("items") or []),
                )
            )
        structure = [
            StructureEntry(path=str(item.get("path", "")), purpose=str(item.get("purpose", "")))
            for item in data.get("structure") or []
        ]
        return GeneratedDoc(
            project_type=project_type,
            title=str(data.get("title") or skeleton.root_name),
            repo_url=skeleton.repo_url,
            overview=str(data.get("overview") or ""),
            getting_started=str(data.get("getting_started") or _getting_started_from_manifests(skeleton)),
            structure=structure,
            sections=sections,
        )
    except Exception:
        return _fallback(skeleton, project_type, summaries)


def _dump(model: ArchitectureDraft | SurfaceDraft | OperationsDraft | None) -> dict | None:
    return None if model is None else model.model_dump()
