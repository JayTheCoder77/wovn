from __future__ import annotations

from skeleton_schema.models import FileSkeleton, Snippet, SnippetReason

MAX_SNIPPETS_PER_FILE = 3
MAX_SNIPPET_LINES = 12
MIN_FILE_LOC = 3


def extract_snippets(path: str, source: str | bytes, file: FileSkeleton) -> list[Snippet]:
    text = source.decode("utf-8", errors="replace") if isinstance(source, bytes) else source
    lines = text.splitlines()
    loc = len(lines) or file.loc
    if loc < MIN_FILE_LOC:
        return []
    if path.endswith(".min.js"):
        return []

    candidates: list[tuple[int, int, SnippetReason]] = []
    if file.is_entry_point:
        line = next((s.line for s in file.symbols if s.name == "main"), None)
        if line is None and file.symbols:
            line = file.symbols[0].line
        candidates.append((0, line or 1, SnippetReason.entry_point))
    export_count = 0
    for symbol in file.symbols:
        if symbol.exported and symbol.kind.value != "method" and export_count < MAX_SNIPPETS_PER_FILE:
            candidates.append((1, max(1, symbol.line), SnippetReason.export))
            export_count += 1
        if symbol.name == "main":
            candidates.append((2, max(1, symbol.line), SnippetReason.main))
    if file.module_doc:
        candidates.append((3, 1, SnippetReason.module_doc))

    candidates.sort(key=lambda item: (item[0], item[1]))
    snippets: list[Snippet] = []
    covered: set[int] = set()
    for _prio, line, reason in candidates:
        if len(snippets) >= MAX_SNIPPETS_PER_FILE:
            break
        start, end = _window(line, loc)
        if any(index in covered for index in range(start, end + 1)):
            continue
        chunk = "\n".join(lines[start - 1 : end])
        if not chunk.strip():
            continue
        snippets.append(
            Snippet(path=path, start_line=start, end_line=end, text=chunk, reason=reason)
        )
        covered.update(range(start, end + 1))
    return snippets


def _window(line: int, loc: int) -> tuple[int, int]:
    start = max(1, line - 5)
    end = min(loc, start + MAX_SNIPPET_LINES - 1)
    start = max(1, min(start, end - MAX_SNIPPET_LINES + 1))
    return start, end
