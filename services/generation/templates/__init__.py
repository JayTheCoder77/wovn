from __future__ import annotations

from doc_schema.models import ProjectType

COMMON = ["overview", "getting_started", "project_structure"]

TYPE_SECTIONS: dict[ProjectType, list[str]] = {
    ProjectType.library: ["api_reference", "usage_examples"],
    ProjectType.web_app: ["architecture", "api_endpoints", "data_models"],
    ProjectType.service: ["architecture", "api_endpoints", "data_models"],
    ProjectType.cli: ["commands_reference", "configuration"],
    ProjectType.general: ["module_breakdown"],
}


def section_plan(project_type: ProjectType) -> list[str]:
    return [*COMMON, *TYPE_SECTIONS[project_type]]
