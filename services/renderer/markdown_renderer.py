from __future__ import annotations

from doc_schema.models import GeneratedDoc


def build_search_index(doc: GeneratedDoc) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = [
        {"id": "overview", "title": "Overview", "text": doc.overview},
        {"id": "getting-started", "title": "Getting started", "text": doc.getting_started},
    ]
    for item in doc.structure:
        entries.append(
            {
                "id": "structure",
                "title": item.path,
                "text": f"{item.path} {item.purpose}",
            }
        )
    for index, section in enumerate(doc.sections):
        blob = section.content + " " + " ".join(str(x) for x in section.items)
        entries.append(
            {
                "id": f"section-{index}",
                "title": section.title,
                "text": blob,
            }
        )
    return entries


def attach_search_index(doc: GeneratedDoc) -> GeneratedDoc:
    doc.search_index = build_search_index(doc)
    return doc
