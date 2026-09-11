from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from skeleton_schema.models import FileSkeleton, PublicApiEntry, RepoSkeleton, SymbolKind

README_DIGEST_CHARS = 1500


def enrich_skeleton(skeleton: RepoSkeleton) -> RepoSkeleton:
    skeleton.readme_digest = readme_digest(skeleton.manifests)
    skeleton.manifest_summary = summarize_manifests(skeleton.manifests)
    skeleton.public_api = public_api(skeleton.files)
    skeleton.test_map = test_map(skeleton.files)
    return skeleton


def readme_digest(manifests: dict[str, Any], limit: int = README_DIGEST_CHARS) -> str | None:
    preferred = ("README.md", "README.rst", "README")
    for key in preferred:
        value = manifests.get(key)
        if isinstance(value, str) and value.strip():
            return value[:limit]
    for key, value in manifests.items():
        if Path(key).name.upper().startswith("README") and isinstance(value, str) and value.strip():
            return value[:limit]
    return None


def summarize_manifests(manifests: dict[str, Any]) -> dict[str, Any]:
    dependencies: list[str] = []
    scripts: list[str] = []
    bins: list[str] = []
    managers: list[str] = []

    for rel, data in manifests.items():
        lower = rel.lower().replace("\\", "/")
        if lower.endswith("pyproject.toml") and isinstance(data, dict):
            managers.append("python")
            project = data.get("project") or {}
            for dep in project.get("dependencies") or []:
                dependencies.append(_dep_name(str(dep)))
            scripts.extend((project.get("scripts") or {}).keys())
        elif lower.endswith("package.json") and isinstance(data, dict):
            managers.append("node")
            dependencies.extend((data.get("dependencies") or {}).keys())
            dependencies.extend((data.get("devDependencies") or {}).keys())
            scripts.extend((data.get("scripts") or {}).keys())
            bin_field = data.get("bin")
            if isinstance(bin_field, str):
                bins.append(Path(rel).name)
            elif isinstance(bin_field, dict):
                bins.extend(bin_field.keys())
        elif lower.endswith("cargo.toml") and isinstance(data, dict):
            managers.append("rust")
            dependencies.extend((data.get("dependencies") or {}).keys())
            package = data.get("package") or {}
            if package.get("name"):
                bins.append(str(package["name"]))
        elif lower.endswith("go.mod") and isinstance(data, str):
            managers.append("go")
            dependencies.extend(_go_mod_deps(data))
        elif lower.endswith("requirements.txt") and isinstance(data, str):
            managers.append("python")
            for line in data.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    dependencies.append(_dep_name(stripped))

    return {
        "package_managers": sorted(set(managers)),
        "dependencies": sorted({item for item in dependencies if item}),
        "scripts": sorted(set(scripts)),
        "bins": sorted(set(bins)),
    }


def public_api(files: list[FileSkeleton]) -> list[PublicApiEntry]:
    entries: list[PublicApiEntry] = []
    for file in files:
        if _is_test_path(file.path):
            continue
        for symbol in file.symbols:
            if not symbol.exported or symbol.kind == SymbolKind.method:
                continue
            entries.append(
                PublicApiEntry(
                    path=file.path,
                    name=symbol.name,
                    kind=symbol.kind,
                    signature=symbol.signature,
                    line=symbol.line,
                )
            )
    return entries


def test_map(files: list[FileSkeleton]) -> dict[str, list[str]]:
    by_name: dict[str, list[str]] = defaultdict(list)
    for file in files:
        by_name[Path(file.path).name].append(file.path)

    mapping: dict[str, list[str]] = defaultdict(list)
    for file in files:
        for source_name in _paired_source_names(Path(file.path).name):
            for source_path in by_name.get(source_name, []):
                if source_path == file.path:
                    continue
                mapping[file.path].append(source_path)
                mapping[source_path].append(file.path)
    return {key: sorted(set(values)) for key, values in mapping.items()}


def _paired_source_names(name: str) -> list[str]:
    if name.startswith("test_") and name.endswith(".py"):
        return [name[len("test_") :]]
    if name.endswith("_test.py"):
        return [name[: -len("_test.py")] + ".py"]
    if ".test." in name:
        return [name.replace(".test.", ".", 1)]
    if ".spec." in name:
        return [name.replace(".spec.", ".", 1)]
    return []


def _is_test_path(path: str) -> bool:
    posix = path.replace("\\", "/")
    name = Path(posix).name
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    if ".test." in name or ".spec." in name:
        return True
    return any(part in {"tests", "test"} for part in posix.split("/")[:-1])


def _dep_name(spec: str) -> str:
    cut = spec.strip().strip("\"'")
    for sep in ("[", "==", ">=", "<=", "~=", "!=", ">", "<", ";"):
        cut = cut.split(sep, 1)[0]
    return cut.strip()


def _go_mod_deps(text: str) -> list[str]:
    deps: list[str] = []
    in_require = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("require ("):
            in_require = True
            continue
        if in_require:
            if line.startswith(")"):
                in_require = False
                continue
            if line and not line.startswith("//"):
                deps.append(line.split()[0])
            continue
        if line.startswith("require ") and "(" not in line:
            parts = line.split()
            if len(parts) >= 2:
                deps.append(parts[1])
    return deps
