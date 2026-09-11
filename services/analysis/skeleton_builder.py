from __future__ import annotations

import json
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from skeleton_schema.models import FileSkeleton, LanguageName, RepoSkeleton

from ingest.sandbox.limits import MAX_FILE_BYTES, MAX_FILES

from analysis.parsers.go import parse_go
from analysis.parsers.javascript import parse_javascript, parse_tsx, parse_typescript
from analysis.parsers.python import parse_python
from analysis.parsers.rust import parse_rust

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "target",
    "dist",
    "build",
    "__pycache__",
    ".next",
    "coverage",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "Pods",
    "site-packages",
}

EXTENSIONS: dict[str, tuple[str, Callable[[str, bytes], FileSkeleton]]] = {
    ".py": ("python", parse_python),
    ".ts": ("typescript", parse_typescript),
    ".tsx": ("tsx", parse_tsx),
    ".js": ("javascript", parse_javascript),
    ".jsx": ("javascript", parse_javascript),
    ".mjs": ("javascript", parse_javascript),
    ".cjs": ("javascript", parse_javascript),
    ".go": ("go", parse_go),
    ".rs": ("rust", parse_rust),
}

MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Cargo.toml",
    "go.mod",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "README.md",
    "README.rst",
    "README",
}


def _read_text_limited(path: Path, limit: int = 80_000) -> str:
    data = path.read_bytes()[:limit]
    return data.decode("utf-8", errors="replace")


def collect_manifests(root: Path) -> dict[str, Any]:
    manifests: dict[str, Any] = {}
    for dirpath, dirnames, filenames in os_walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        if any(part in SKIP_DIRS for part in rel_dir.parts):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if len(rel_dir.parts) > 2:
            continue
        for name in filenames:
            if name not in MANIFEST_NAMES:
                continue
            path = Path(dirpath) / name
            rel = str(path.relative_to(root)).replace("\\", "/")
            try:
                if name == "package.json":
                    manifests[rel] = json.loads(_read_text_limited(path))
                elif name in {"pyproject.toml", "Cargo.toml"}:
                    manifests[rel] = tomllib.loads(_read_text_limited(path))
                else:
                    manifests[rel] = _read_text_limited(path, 20_000)
            except Exception:
                manifests[rel] = _read_text_limited(path, 8_000)
    return manifests


def os_walk(root: Path):
    import os

    return os.walk(root)


def _iter_source_files(root: Path):
    count = 0
    for dirpath, dirnames, filenames in os_walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        if any(part in SKIP_DIRS for part in rel_dir.parts):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            suffix = Path(filename).suffix.lower()
            if suffix not in EXTENSIONS:
                continue
            if filename.endswith(".min.js") or filename.endswith(".d.ts"):
                continue
            path = Path(dirpath) / filename
            rel = str(path.relative_to(root)).replace("\\", "/")
            yield path, rel, suffix
            count += 1
            if count >= MAX_FILES:
                return


def _resolve_local_import(from_path: str, module: str, files_by_path: set[str]) -> str | None:
    if not module.startswith("."):
        return None
    base = Path(from_path).parent
    target = (base / module).as_posix()
    candidates = [
        target,
        f"{target}.py",
        f"{target}.ts",
        f"{target}.tsx",
        f"{target}.js",
        f"{target}.jsx",
        f"{target}.go",
        f"{target}.rs",
        f"{target}/index.ts",
        f"{target}/index.js",
        f"{target}/__init__.py",
        f"{target}.mod.rs",
    ]
    for candidate in candidates:
        normalized = str(Path(candidate)).replace("\\", "/")
        if normalized in files_by_path:
            return normalized
    return None


def build_skeleton(root: Path, repo_url: str, root_name: str) -> RepoSkeleton:
    files: list[FileSkeleton] = []
    languages: set[LanguageName] = set()
    tree_paths: list[str] = []

    for path, rel, suffix in _iter_source_files(root):
        tree_paths.append(rel)
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            continue
        try:
            source = path.read_bytes()
        except OSError:
            continue
        _parser_key, parse = EXTENSIONS[suffix]
        try:
            parsed = parse(rel, source)
        except Exception:
            continue
        files.append(parsed)
        languages.add(parsed.language)

    files_by_path = {f.path for f in files}
    import_graph: dict[str, list[str]] = defaultdict(list)
    for file in files:
        seen: set[str] = set()
        for item in file.imports:
            resolved = _resolve_local_import(file.path, item.module, files_by_path)
            target = resolved or item.module
            if target in seen:
                continue
            seen.add(target)
            import_graph[file.path].append(target)

    entry_points = [f.path for f in files if f.is_entry_point]
    manifests = collect_manifests(root)

    return RepoSkeleton(
        repo_url=repo_url,
        root_name=root_name,
        languages=sorted(languages, key=lambda x: x.value),
        file_count=len(files),
        loc=sum(f.loc for f in files),
        files=files,
        tree=sorted(tree_paths),
        import_graph=dict(import_graph),
        entry_points=entry_points,
        manifests=manifests,
    )
