"""Compiler configuration types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class CompilationMode(StrEnum):
    """Compilation behavior mode."""

    NORMAL = "normal"
    STRICT = "strict"
    LENIENT = "lenient"


@dataclass(frozen=True)
class CompilerConfig:
    """Configuration shared across compiler entrypoints."""

    mode: CompilationMode = CompilationMode.NORMAL
    scope_root: Path | None = None
    use_parse_cache: bool = True
    profile: str | None = None
    pinned_timestamp: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
