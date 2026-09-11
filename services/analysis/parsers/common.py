from __future__ import annotations

from tree_sitter import Language, Parser

_PARSERS: dict[str, Parser] = {}


def get_parser(language: str) -> Parser:
    cached = _PARSERS.get(language)
    if cached is not None:
        return cached

    if language == "python":
        import tree_sitter_python as grammar

        lang = Language(grammar.language())
    elif language == "javascript":
        import tree_sitter_javascript as grammar

        lang = Language(grammar.language())
    elif language == "typescript":
        import tree_sitter_typescript as grammar

        lang = Language(grammar.language_typescript())
    elif language == "tsx":
        import tree_sitter_typescript as grammar

        lang = Language(grammar.language_tsx())
    elif language == "go":
        import tree_sitter_go as grammar

        lang = Language(grammar.language())
    elif language == "rust":
        import tree_sitter_rust as grammar

        lang = Language(grammar.language())
    else:
        raise ValueError(f"Unsupported parser language: {language}")

    parser = Parser(lang)
    _PARSERS[language] = parser
    return parser


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def node_text(source: bytes, node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def first_line_signature(source: bytes, node, limit: int = 240) -> str:
    text = " ".join(node_text(source, node).strip().split())
    for sep in (" {", ":", " where ", " implements "):
        idx = text.find(sep)
        if idx > 0:
            text = text[:idx].strip()
            break
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def line_no(node) -> int:
    return int(node.start_point[0]) + 1
