from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    web_app = "web_app"
    library = "library"
    cli = "cli"
    service = "service"
    general = "general"


class StructureEntry(BaseModel):
    path: str
    purpose: str


class DocSection(BaseModel):
    type: str
    title: str
    content: str = ""
    diagram: str | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)


class GeneratedDoc(BaseModel):
    project_type: ProjectType
    title: str
    repo_url: str = ""
    overview: str
    getting_started: str = ""
    structure: list[StructureEntry] = Field(default_factory=list)
    sections: list[DocSection] = Field(default_factory=list)
    search_index: list[dict[str, str]] = Field(default_factory=list)
