"""Pure-text helpers for incremental search and query-replace.

All functions operate on the plain ``str`` returned by ``TextArea.text``.
Charater indices count every character including newlines, so that they map
1:1 onto document locations.
"""

from __future__ import annotations

import re


def index_to_location(text: str, index: int) -> tuple[int, int]:
    """Convert a flat character index to a ``(row, column)`` location."""
    index = max(0, min(index, len(text)))
    line = 0
    start = 0
    for offset, char in enumerate(text):
        if offset == index:
            break
        if char == "\n":
            line += 1
            start = offset + 1
    return (line, index - start)


def location_to_index(text: str, location: tuple[int, int]) -> int:
    """Convert a ``(row, column)`` location to a flat character index."""
    row, column = location
    lines = text.split("\n")
    if row >= len(lines):
        return len(text)
    line = lines[row]
    column = max(0, min(column, len(line)))
    return sum(len(l) + 1 for l in lines[:row]) + column


def find_all(text: str, query: str, *, case_sensitive: bool = False) -> list[tuple[int, int]]:
    """Return the character-index ranges of every match of *query* in *text*."""
    if not query:
        return []
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(query), flags)
    return [(m.start(), m.end()) for m in pattern.finditer(text)]


def next_match(
    text: str,
    query: str,
    from_index: int,
    *,
    direction: int = 1,
    case_sensitive: bool = False,
) -> tuple[int, int] | None:
    """Find the next match at or after *from_index* (forward or backward).

    Forward search is inclusive of *from_index*; backward search starts at
    ``from_index - 1`` so that the current match is not returned again.
    Wraps around the document.
    """
    matches = find_all(text, query, case_sensitive=case_sensitive)
    if not matches:
        return None
    if direction >= 0:
        for start, end in matches:
            if start >= from_index:
                return (start, end)
        return matches[0]
    for start, end in reversed(matches):
        if end < from_index:
            return (start, end)
    return matches[-1]
