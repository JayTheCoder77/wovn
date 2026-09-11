from __future__ import annotations

from skeleton_schema.models import FileSkeleton, Import, LanguageName, Symbol, SymbolKind

from analysis.parsers.common import first_line_signature, get_parser, line_no, node_text, walk


def parse_go(path: str, source: bytes) -> FileSkeleton:
    tree = get_parser("go").parse(source)
    imports: list[Import] = []
    symbols: list[Symbol] = []
    package_name = ""
    has_main = False

    for node in walk(tree.root_node):
        if node.type == "package_clause":
            package_name = node_text(source, node).replace("package", "").strip()
        elif node.type == "import_spec":
            raw = node_text(source, node).strip().strip('"')
            path_node = node.child_by_field_name("path")
            module = node_text(source, path_node).strip('"') if path_node else raw
            imports.append(Import(raw=raw, module=module))
        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            name = node_text(source, name_node) if name_node else "fn"
            symbols.append(
                Symbol(
                    name=name,
                    kind=SymbolKind.function,
                    signature=first_line_signature(source, node),
                    exported=bool(name) and name[0].isupper(),
                    line=line_no(node),
                )
            )
            if name == "main":
                has_main = True
        elif node.type == "method_declaration":
            name_node = node.child_by_field_name("name")
            name = node_text(source, name_node) if name_node else "method"
            symbols.append(
                Symbol(
                    name=name,
                    kind=SymbolKind.method,
                    signature=first_line_signature(source, node),
                    exported=bool(name) and name[0].isupper(),
                    line=line_no(node),
                )
            )
        elif node.type == "type_declaration":
            for child in walk(node):
                if child.type in {"type_spec", "type_alias"}:
                    name_node = child.child_by_field_name("name")
                    if name_node is None:
                        continue
                    name = node_text(source, name_node)
                    type_node = child.child_by_field_name("type")
                    kind = SymbolKind.struct
                    if type_node is not None and type_node.type == "interface_type":
                        kind = SymbolKind.interface
                    symbols.append(
                        Symbol(
                            name=name,
                            kind=kind,
                            signature=first_line_signature(source, child),
                            exported=bool(name) and name[0].isupper(),
                            line=line_no(child),
                        )
                    )

    loc = source.count(b"\n") + (0 if source.endswith(b"\n") or not source else 1)
    return FileSkeleton(
        path=path,
        language=LanguageName.go,
        loc=loc,
        imports=imports,
        symbols=symbols,
        is_entry_point=package_name == "main" and has_main,
        module_doc=f"package {package_name}" if package_name else None,
    )
