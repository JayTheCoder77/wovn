from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    path: str
    line: int = 1


class RunPlan(BaseModel):
    module_names: list[str] = Field(default_factory=list)
    run_architecture: bool = True
    run_surface: bool = True
    run_operations: bool = True
    run_critic: bool = False
    rationale: str = ""


class ArchitectureDraft(BaseModel):
    narrative: str = ""
    components: list[dict[str, Any]] = Field(default_factory=list)
    diagram: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class SurfaceDraft(BaseModel):
    section_type: str = "api_reference"
    title: str = ""
    content: str = ""
    items: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class OperationsDraft(BaseModel):
    getting_started: str = ""
    env_var_names: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class CriticReport(BaseModel):
    unsupported: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    ok: bool = True
