from __future__ import annotations

import tiktoken

_ENCODING = None


def encoding():
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(encoding().encode(text))
