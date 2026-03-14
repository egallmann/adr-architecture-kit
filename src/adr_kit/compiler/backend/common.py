"""Shared backend emission types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EmittedArtifact:
    """Serialized artifact payload produced by a backend emitter."""

    path: Path
    content: bytes
    kind: str
    integrity_header: str | None = None
