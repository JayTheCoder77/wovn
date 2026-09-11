from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skeleton_schema.models import FileSkeleton, PublicApiEntry, RepoSkeleton, Snippet, SnippetReason

from renderer.diagram_gen import mermaid_from_import_graph

GLOBAL_TOKEN_CAP = 2000
MODULE_TOKEN_CAP = 2500
MAX_GRAPH_EDGES = 40
MAX_PUBLIC_API = 80
MAX_TREE = 120
SNIPPET_DROP_ORDER = (
    SnippetReason.module_doc,
    SnippetReason.main,
    SnippetReason.export,
    SnippetReason.entry_point,
)


@dataclass
class GlobalPack:
    root_name: str
    repo_url: str
    languages: list[str]
    entry_points: list[str]
    readme_digest: str | None
    manifest_summary: dict[str, Any]
    import_graph_summary: str
    public_api: list[PublicApiEntry]
    tree: list[str]
    trimmed: bool = False


@dataclass
class ModulePack:
    name: str
    files: list[FileSkeleton]
    test_map: dict[str, list[str]] = field(default_factory=dict)
    trimmed: bool = False


@dataclass
class ContextPacks:
    global_pack: GlobalPack
    modules: list[ModulePack]


def build_context_packs(
    skeleton: RepoSkeleton,
    *,
    module_token_cap: int = MODULE_TOKEN_CAP,
    global_token_cap: int = GLOBAL_TOKEN_CAP,
) -> ContextPacks:
    modules: list[ModulePack] = []
    for group in group_files(skeleton.files):
        files = [file.model_copy(deep=True) for file in group.files]
        for file in files:
            file.symbols = file.symbols[:MAX_SYMBOLS_CONTEXT]
        related = {
            file.path: list(skeleton.test_map.get(file.path, []))
            for file in files
            if file.path in skeleton.test_map
        }
        pack = ModulePack(name=group.name, files=files, test_map=related)
        _trim_module(pack, module_token_cap)
        modules.append(pack)

    global_pack = GlobalPack(
        root_name=skeleton.root_name,
        repo_url=skeleton.repo_url,
        languages=[lang.value for lang in skeleton.languages],
        entry_points=list(skeleton.entry_points),
        readme_digest=skeleton.readme_digest,
        manifest_summary=dict(skeleton.manifest_summary or {}),
        import_graph_summary=_mermaid_edges(skeleton.import_graph),
        public_api=list(skeleton.public_api[:MAX_PUBLIC_API]),
        tree=list(skeleton.tree[:MAX_TREE]),
    )
    _trim_global(global_pack, global_token_cap)
    return ContextPacks(global_pack=global_pack, modules=modules)


def render_global_pack(pack: GlobalPack) -> str:
    api_lines = [
        f"- {entry.path}:{entry.line} {entry.kind.value} {entry.signature}"
        for entry in pack.public_api
    ]
    return "\n".join(
        [
            f"REPO {pack.root_name} {pack.repo_url}",
            f"LANGUAGES: {', '.join(pack.languages)}",
            f"ENTRY_POINTS: {', '.join(pack.entry_points)}",
            f"README:\n{pack.readme_digest or ''}",
            f"MANIFEST_SUMMARY: {pack.manifest_summary}",
            "PUBLIC_API:",
            *api_lines,
            "IMPORT_GRAPH:",
            pack.import_graph_summary,
            "TREE:",
            *pack.tree,
        ]
    )


def render_module_pack(pack: ModulePack) -> str:
    blocks = [f"MODULE {pack.name}", f"TEST_MAP: {pack.test_map}"]
    for file in pack.files:
        symbols = "\n".join(
            f"- {s.kind.value} {s.signature} exported={s.exported} line={s.line}"
            + (f" // {s.docstring}" if s.docstring else "")
            for s in file.symbols
        )
        imports = ", ".join(item.module for item in file.imports[:30])
        snippet_blocks = []
        for snippet in file.snippets:
            provenance = f"{snippet.path}:{snippet.start_line}-{snippet.end_line}"
            snippet_blocks.append(
                f"SNIPPET {provenance} reason={snippet.reason.value}\n{snippet.text}"
            )
        blocks.append(
            f"FILE: {file.path} ({file.language.value}, {file.loc} loc)\n"
            f"ENTRY={file.is_entry_point}\n"
            f"IMPORTS: {imports}\n"
            f"SYMBOLS:\n{symbols or '- none'}\n"
            f"DOC: {file.module_doc or ''}\n"
            + ("\n".join(snippet_blocks) + "\n" if snippet_blocks else "")
        )
    return "\n".join(blocks)


def _trim_module(pack: ModulePack, cap: int) -> None:
    if count_tokens(render_module_pack(pack)) <= cap:
        return
    pack.trimmed = True
    for reason in SNIPPET_DROP_ORDER:
        if count_tokens(render_module_pack(pack)) <= cap:
            return
        for file in pack.files:
            file.snippets = [s for s in file.snippets if s.reason != reason]
            if count_tokens(render_module_pack(pack)) <= cap:
                return
    while count_tokens(render_module_pack(pack)) > cap:
        shortened = False
        for file in pack.files:
            if len(file.symbols) > 1:
                file.symbols = file.symbols[:-1]
                shortened = True
                if count_tokens(render_module_pack(pack)) <= cap:
                    return
        if not shortened:
            return


def _trim_global(pack: GlobalPack, cap: int) -> None:
    if count_tokens(render_global_pack(pack)) <= cap:
        return
    pack.trimmed = True
    while count_tokens(render_global_pack(pack)) > cap:
        changed = False
        if pack.readme_digest and len(pack.readme_digest) > 80:
            pack.readme_digest = pack.readme_digest[: max(40, len(pack.readme_digest) // 2)]
            changed = True
        elif len(pack.public_api) > 4:
            pack.public_api = pack.public_api[: len(pack.public_api) // 2]
            changed = True
        elif len(pack.tree) > 8:
            pack.tree = pack.tree[: len(pack.tree) // 2]
            changed = True
        elif pack.import_graph_summary.count("\n") > 2:
            lines = pack.import_graph_summary.splitlines()
            pack.import_graph_summary = "\n".join(lines[: max(2, len(lines) // 2)])
            changed = True
        elif pack.manifest_summary:
            pack.manifest_summary = {}
            changed = True
        if not changed:
            return


def _mermaid_edges(import_graph: dict[str, list[str]]) -> str:
    return mermaid_from_import_graph(import_graph, limit=MAX_GRAPH_EDGES) or "flowchart LR\n  none[no edges]"
