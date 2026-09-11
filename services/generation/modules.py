from __future__ import annotations

from dataclasses import dataclass

from skeleton_schema.models import FileSkeleton

MAX_FILES_PER_MODULE = 12
MAX_SYMBOLS_CONTEXT = 40


def file_context(file: FileSkeleton) -> str:
    symbols = "\n".join(
        f"- {s.kind.value} {s.signature} exported={s.exported}"
        + (f" // {s.docstring}" if s.docstring else "")
        for s in file.symbols[:MAX_SYMBOLS_CONTEXT]
    )
    imports = ", ".join(item.module for item in file.imports[:30])
    return (
        f"FILE {file.path} ({file.language.value}, {file.loc} loc)\n"
        f"ENTRY={file.is_entry_point}\n"
        f"IMPORTS: {imports}\n"
        f"SYMBOLS:\n{symbols or '- none'}\n"
        f"DOC: {file.module_doc or ''}\n"
    )


@dataclass
class ModuleGroup:
    name: str
    files: list[FileSkeleton]


def _top_dir(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    if len(parts) == 1:
        return "_root"
    return parts[0]


def group_files(files: list[FileSkeleton]) -> list[ModuleGroup]:
    """Group files by top-level directory, then split oversized groups.

    Empty-symbol files still count toward structure but are skipped unless they
    are entry points or the group would otherwise be empty.
    """
    buckets: dict[str, list[FileSkeleton]] = {}
    for file in files:
        buckets.setdefault(_top_dir(file.path), []).append(file)

    groups: list[ModuleGroup] = []
    for name in sorted(buckets):
        items = sorted(buckets[name], key=lambda f: f.path)
        meaningful = [f for f in items if f.symbols or f.is_entry_point or f.imports]
        use = meaningful or items
        for index in range(0, len(use), MAX_FILES_PER_MODULE):
            chunk = use[index : index + MAX_FILES_PER_MODULE]
            suffix = "" if index == 0 else f"/{index // MAX_FILES_PER_MODULE + 1}"
            groups.append(ModuleGroup(name=f"{name}{suffix}", files=chunk))
    return groups or [ModuleGroup(name="_root", files=files[:MAX_FILES_PER_MODULE])]
