from __future__ import annotations

from skeleton_schema.models import FileSkeleton, Import, LanguageName, Symbol, SymbolKind

from analysis.parsers.common import first_line_signature, get_parser, line_no, node_text, walk


def _is_pub(node) -> bool:
    current = node
    # visibility_modifier is typically a child of the item
    for child in node.children:
        if child.type == "visibility_modifier":
            return True
        if child.type == "function_modifiers":
            for nested in child.children:
                if nested.type == "visibility_modifier":
                    return True
    while current is not None:
        if current.type == "visibility_modifier":
            return True
        current = current.parent
    return False


def parse_rust(path: str, source: bytes) -> FileSkeleton:
    tree = get_parser("rust").parse(source)
    imports: list[Import] = []
    symbols: list[Symbol] = []
    is_entry = False

    for node in walk(tree.root_node):
        if node.type == "use_declaration":
            raw = node_text(source, node).strip()
            imports.append(Import(raw=raw, module=raw.replace("use ", "").rstrip(";")))
        elif node.type == "function_item":
            name_node = node.child_by_field_name("name")
            name = node_text(source, name_node) if name_node else "fn"
            symbols.append(
                Symbol(
                    name=name,
                    kind=SymbolKind.function,
                    signature=first_line_signature(source, node),
                    exported=_is_pub(node),
                    line=line_no(node),
                )
            )
            if name == "main":
                is_entry = True
        elif node.type == "struct_item":
            name_node = node.child_by_field_name("name")
            name = node_text(source, name_node) if name_node else "struct"
            symbols.append(
                Symbol(
                    name=name,
                    kind=SymbolKind.struct,
                    signature=first_line_signature(source, node),
                    exported=_is_pub(node),
                    line=line_no(node),
                )
            )
        elif node.type == "enum_item":
            name_node = node.child_by_field_name("name")
            name = node_text(source, name_node) if name_node else "enum"
            symbols.append(
                Symbol(
                    name=name,
                    kind=SymbolKind.enum,
                    signature=first_line_signature(source, node),
                    exported=_is_pub(node),
                    line=line_no(node),
                )
            )
        elif node.type == "trait_item":
            name_node = node.child_by_field_name("name")
            name = node_text(source, name_node) if name_node else "trait"
            symbols.append(
                Symbol(
                    name=name,
                    kind=SymbolKind.trait,
                    signature=first_line_signature(source, node),
                    exported=_is_pub(node),
                    line=line_no(node),
                )
            )
        elif node.type == "mod_item":
            name_node = node.child_by_field_name("name")
            name = node_text(source, name_node) if name_node else "mod"
            symbols.append(
                Symbol(
                    name=name,
                    kind=SymbolKind.module,
                    signature=first_line_signature(source, node),
                    exported=_is_pub(node),
                    line=line_no(node),
                )
            )

    loc = source.count(b"\n") + (0 if source.endswith(b"\n") or not source else 1)
    return FileSkeleton(
        path=path,
        language=LanguageName.rust,
        loc=loc,
        imports=imports,
        symbols=symbols,
        is_entry_point=is_entry,
    )
