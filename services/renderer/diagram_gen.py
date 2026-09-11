from __future__ import annotations

from doc_schema.models import GeneratedDoc


def mermaid_from_import_graph(graph: dict[str, list[str]], limit: int = 40) -> str:
    lines = ["flowchart LR"]
    count = 0
    for source, targets in list(graph.items())[:limit]:
        src = _id(source)
        for target in targets[:6]:
            if "/" not in target and "." not in target:
                continue
            if not target.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs")):
                continue
            lines.append(f'  {src}["{source}"] --> {_id(target)}["{target}"]')
            count += 1
            if count >= limit:
                break
        if count >= limit:
            break
    if count == 0:
        return ""
    return "\n".join(lines)


def _id(path: str) -> str:
    return "n" + "".join(ch if ch.isalnum() else "_" for ch in path)[:80]


def ensure_architecture_diagram(doc: GeneratedDoc, mermaid: str) -> GeneratedDoc:
    if not mermaid:
        return doc
    for section in doc.sections:
        if section.type == "architecture":
            section.diagram = mermaid
    return doc
