"""Parsed source corpus container."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedCorpus:
    """Holds parsed source artifacts keyed by source path."""

    artifacts: dict[str, Any] = field(default_factory=dict)

    def add(self, path: Path | str, artifact: Any) -> None:
        self.artifacts[str(path)] = artifact
