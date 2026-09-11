from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LanguageName(str, Enum):
    python = "python"
    typescript = "typescript"
    javascript = "javascript"
    go = "go"
    rust = "rust"


class SymbolKind(str, Enum):
    function = "function"
    method = "method"
    class_ = "class"
    interface = "interface"
    type_alias = "type"
    struct = "struct"
    enum = "enum"
    trait = "trait"
    const = "const"
    variable = "variable"
    module = "module"


class Symbol(BaseModel):
    name: str
    kind: SymbolKind
    signature: str
    exported: bool = False
    line: int = 1
    docstring: str | None = None


class Import(BaseModel):
    raw: str
    module: str
    names: list[str] = Field(default_factory=list)
    is_relative: bool = False


class SnippetReason(str, Enum):
    entry_point = "entry_point"
    export = "export"
    main = "main"
    module_doc = "module_doc"


class Snippet(BaseModel):
    path: str
    start_line: int
    end_line: int
    text: str
    reason: SnippetReason


class PublicApiEntry(BaseModel):
    path: str
    name: str
    kind: SymbolKind
    signature: str
    line: int = 1


class FileSkeleton(BaseModel):
    path: str
    language: LanguageName
    loc: int = 0
    imports: list[Import] = Field(default_factory=list)
    symbols: list[Symbol] = Field(default_factory=list)
    is_entry_point: bool = False
    module_doc: str | None = None
    snippets: list[Snippet] = Field(default_factory=list)


class RepoSkeleton(BaseModel):
    repo_url: str
    root_name: str
    languages: list[LanguageName] = Field(default_factory=list)
    file_count: int = 0
    loc: int = 0
    files: list[FileSkeleton] = Field(default_factory=list)
    tree: list[str] = Field(default_factory=list)
    import_graph: dict[str, list[str]] = Field(default_factory=dict)
    entry_points: list[str] = Field(default_factory=list)
    manifests: dict[str, Any] = Field(default_factory=dict)
    classifier_signals: dict[str, Any] = Field(default_factory=dict)
    readme_digest: str | None = None
    manifest_summary: dict[str, Any] = Field(default_factory=dict)
    public_api: list[PublicApiEntry] = Field(default_factory=list)
    test_map: dict[str, list[str]] = Field(default_factory=dict)
