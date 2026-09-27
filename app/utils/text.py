"""Split long plain-text answers at natural boundaries."""

from __future__ import annotations


def split_text(text: str, limit: int = 4000) -> list[str]:
    if limit < 2:
        raise ValueError("limit must be at least 2")
    remaining = text.strip()
    chunks: list[str] = []
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", limit // 2, limit + 1)
        if cut < 0:
            cut = remaining.rfind(" ", limit // 2, limit + 1)
        if cut < 0:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks
