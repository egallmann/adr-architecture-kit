"""Shared backend emission types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..diagnostics import Diagnostic


@dataclass(frozen=True)
class EmittedArtifact:
    """Serialized artifact payload produced by a backend emitter."""

    path: Path
    content: bytes
    kind: str
    integrity_header: str | None = None


class BackendEmitter(Protocol):
    """Minimal static backend-emitter contract for the unified driver."""

    name: str
    artifact_group: str

    def emit(self) -> list[EmittedArtifact]:
        """Emit artifacts for one static compiler backend group."""

    def diagnostics(self) -> list[Diagnostic]:
        """Return deterministic diagnostics produced during emission."""
