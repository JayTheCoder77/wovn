from __future__ import annotations

from skeleton_schema.models import FileSkeleton, Import, LanguageName, Symbol, SymbolKind

from analysis.parsers.common import first_line_signature, get_parser, line_no, node_text, walk


_EXPORT_PARENTS = {"export_statement", "export_clause", "lexical_declaration"}
_FUNC_TYPES = {
    "function_declaration",
    "generator_function_declaration",
    "function_signature",
    "method_definition",
    "method_signature",
}
_CLASS_TYPES = {"class_declaration", "abstract_class_declaration"}
_TYPE_TYPES = {"interface_declaration", "type_alias_declaration", "enum_declaration"}


def _exported(node) -> bool:
    current = node
    while current is not None:
        if current.type == "export_statement":
            return True
        current = current.parent
    return False


def _name_from_node(source: bytes, node) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return node_text(source, name_node)
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "property_identifier"):
            return node_text(source, child)
    return first_line_signature(source, node, limit=80)


def _parse_ecma(path: str, source: bytes, parser_lang: str, language: LanguageName) -> FileSkeleton:
    tree = get_parser(parser_lang).parse(source)
    imports: list[Import] = []
    symbols: list[Symbol] = []
    is_entry = False

    for node in walk(tree.root_node):
        if node.type == "import_statement":
            raw = node_text(source, node).strip()
            source_node = node.child_by_field_name("source")
            module = node_text(source, source_node).strip("\"'") if source_node else raw
            imports.append(
                Import(
                    raw=raw,
                    module=module,
                    is_relative=module.startswith("."),
                )
            )
        elif node.type in _FUNC_TYPES:
            name = _name_from_node(source, node)
            kind = SymbolKind.method if node.type in {"method_definition", "method_signature"} else SymbolKind.function
            symbols.append(
                Symbol(
                    name=name,
                    kind=kind,
                    signature=first_line_signature(source, node),
                    exported=_exported(node) or name in {"default"},
                    line=line_no(node),
                )
            )
            if name in {"main", "cli"}:
                is_entry = True
        elif node.type in _CLASS_TYPES:
            symbols.append(
                Symbol(
                    name=_name_from_node(source, node),
                    kind=SymbolKind.class_,
                    signature=first_line_signature(source, node),
                    exported=_exported(node),
                    line=line_no(node),
                )
            )
        elif node.type == "interface_declaration":
            symbols.append(
                Symbol(
                    name=_name_from_node(source, node),
                    kind=SymbolKind.interface,
                    signature=first_line_signature(source, node),
                    exported=_exported(node),
                    line=line_no(node),
                )
            )
        elif node.type == "type_alias_declaration":
            symbols.append(
                Symbol(
                    name=_name_from_node(source, node),
                    kind=SymbolKind.type_alias,
                    signature=first_line_signature(source, node),
                    exported=_exported(node),
                    line=line_no(node),
                )
            )
        elif node.type == "enum_declaration":
            symbols.append(
                Symbol(
                    name=_name_from_node(source, node),
                    kind=SymbolKind.enum,
                    signature=first_line_signature(source, node),
                    exported=_exported(node),
                    line=line_no(node),
                )
            )
        elif node.type == "export_statement":
            raw = node_text(source, node)
            if "default" in raw:
                is_entry = is_entry or "createRoot" in raw or "ReactDOM" in raw

    loc = source.count(b"\n") + (0 if source.endswith(b"\n") or not source else 1)
    return FileSkeleton(
        path=path,
        language=language,
        loc=loc,
        imports=imports,
        symbols=symbols,
        is_entry_point=is_entry,
    )


def parse_javascript(path: str, source: bytes) -> FileSkeleton:
    return _parse_ecma(path, source, "javascript", LanguageName.javascript)


def parse_typescript(path: str, source: bytes) -> FileSkeleton:
    return _parse_ecma(path, source, "typescript", LanguageName.typescript)


def parse_tsx(path: str, source: bytes) -> FileSkeleton:
    return _parse_ecma(path, source, "tsx", LanguageName.typescript)
