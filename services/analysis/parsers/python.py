from __future__ import annotations

from skeleton_schema.models import FileSkeleton, Import, LanguageName, Symbol, SymbolKind

from analysis.parsers.common import first_line_signature, get_parser, line_no, node_text, walk


def _docstring(source: bytes, node) -> str | None:
    body = next((c for c in node.children if c.type == "block"), None)
    if body is None:
        return None
    for child in body.children:
        if child.type != "expression_statement":
            if child.type in ("string", "concatenated_string"):
                raw = node_text(source, child).strip()
                return raw.strip("\"'")
            continue
        inner = child.children[0] if child.children else None
        if inner is not None and inner.type in ("string", "concatenated_string"):
            raw = node_text(source, inner).strip()
            if raw.startswith(('"""', "'''", '"', "'")):
                return raw.strip("\"'").strip()
            return raw
        break
    return None


def parse_python(path: str, source: bytes) -> FileSkeleton:
    tree = get_parser("python").parse(source)
    imports: list[Import] = []
    symbols: list[Symbol] = []
    is_entry = False
    module_doc = None

    root = tree.root_node
    for child in root.children:
        if child.type == "expression_statement" and module_doc is None:
            inner = child.children[0] if child.children else None
            if inner is not None and inner.type in ("string", "concatenated_string"):
                module_doc = node_text(source, inner).strip().strip("\"'").strip()[:400]
        break

    for node in walk(root):
        if node.type == "import_statement":
            raw = node_text(source, node).strip()
            names = [node_text(source, n) for n in walk(node) if n.type == "dotted_name"]
            module = names[0] if names else raw
            imports.append(Import(raw=raw, module=module, names=names))
        elif node.type == "import_from_statement":
            raw = node_text(source, node).strip()
            module_node = node.child_by_field_name("module_name")
            module = node_text(source, module_node) if module_node else ""
            dotted = [node_text(source, n) for n in walk(node) if n.type in ("dotted_name", "relative_import")]
            if not module and dotted:
                module = dotted[0]
            imports.append(
                Import(
                    raw=raw,
                    module=module or raw,
                    names=dotted[1:],
                    is_relative=raw.startswith("from ."),
                )
            )
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node is None:
                continue
            name = node_text(source, name_node)
            parent_is_class = node.parent is not None and node.parent.type == "block" and (
                node.parent.parent is not None and node.parent.parent.type == "class_definition"
            )
            kind = SymbolKind.method if parent_is_class else SymbolKind.function
            symbols.append(
                Symbol(
                    name=name,
                    kind=kind,
                    signature=first_line_signature(source, node),
                    exported=not name.startswith("_"),
                    line=line_no(node),
                    docstring=_docstring(source, node),
                )
            )
            if name == "main" and not parent_is_class:
                is_entry = True
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node is None:
                continue
            name = node_text(source, name_node)
            symbols.append(
                Symbol(
                    name=name,
                    kind=SymbolKind.class_,
                    signature=first_line_signature(source, node),
                    exported=not name.startswith("_"),
                    line=line_no(node),
                    docstring=_docstring(source, node),
                )
            )
        elif node.type == "if_statement":
            cond = node.child_by_field_name("condition")
            if cond is not None and "__name__" in node_text(source, cond):
                is_entry = True

    loc = source.count(b"\n") + (0 if source.endswith(b"\n") or not source else 1)
    return FileSkeleton(
        path=path,
        language=LanguageName.python,
        loc=loc,
        imports=imports,
        symbols=symbols,
        is_entry_point=is_entry,
        module_doc=module_doc,
    )
