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


class FileSkeleton(BaseModel):
    path: str
    language: LanguageName
    loc: int = 0
    imports: list[Import] = Field(default_factory=list)
    symbols: list[Symbol] = Field(default_factory=list)
    is_entry_point: bool = False
    module_doc: str | None = None


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
