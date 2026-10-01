"""Projection Markdown byte helpers for repository-admissible human docs.

Owned by documentation-projection concerns (ADR-L-0007). Keeps newline policy and
authored Markdown hard-break canonicalization out of host/generator-specific
modules and out of indiscriminate post-render whitespace stripping.
"""

from __future__ import annotations

import re

_FENCE_OPEN = re.compile(r"^(?P<indent>\s*)(?P<fence>`{3,}|~{3,})")
_TRAILING_HORIZONTAL = re.compile(r"[ \t]+$")


def canonicalize_projection_newlines(body: str) -> str:
    """Normalize projection Markdown newlines to LF without changing other bytes."""
    return body.replace("\r\n", "\n").replace("\r", "\n")


def canonicalize_authored_markdown_hard_breaks(text: str) -> str:
    """Convert Markdown hard breaks to repository-admissible `<br>` outside fences.

    A Markdown hard break is two or more trailing spaces before a newline.
    Those breaks are rewritten as an explicit `<br>` so meaning is preserved
    without inadmissible trailing horizontal whitespace.

    Fenced code / Mermaid blocks are left untouched so literal spaces remain
    data. Single trailing spaces outside fences are removed as non-semantic
    inadmissible noise, not hard breaks.
    """
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    out: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for index, line in enumerate(lines):
        is_last = index == len(lines) - 1
        fence_match = _FENCE_OPEN.match(line)
        if fence_match is not None:
            marker = fence_match.group("fence")
            char = marker[0]
            length = len(marker)
            if not in_fence:
                in_fence = True
                fence_char = char
                fence_len = length
            elif char == fence_char and length >= fence_len:
                in_fence = False
                fence_char = ""
                fence_len = 0
            out.append(line)
            continue

        if in_fence:
            out.append(line)
            continue

        trailing = _TRAILING_HORIZONTAL.search(line)
        if trailing is None:
            out.append(line)
            continue

        core = line[: trailing.start()]
        spaces = trailing.group(0)
        # Hard breaks require a following newline; the final line of a value is not
        # a hard break even when it ends with spaces.
        if not is_last and len(spaces) >= 2 and set(spaces) == {" "}:
            out.append(f"{core}<br>")
        else:
            out.append(core)

    return "\n".join(out)


def finalize_repository_admissible_markdown(body: str) -> str:
    """Emit repository-admissible projection Markdown without blanket rstrip.

    Applies fence-aware authored hard-break canonicalization, then LF newline
    policy. Does not strip horizontal whitespace inside fenced regions.
    """
    return canonicalize_projection_newlines(canonicalize_authored_markdown_hard_breaks(body))
