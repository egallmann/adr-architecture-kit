"""Shared integrity inputs for the legacy entity registry artifact."""

from __future__ import annotations

from pathlib import Path

from ..scope import ProjectScope
from .core import GeneratorIdentity

LEGACY_ENTITY_REGISTRY_GENERATOR = GeneratorIdentity("adr-compiler", 1)


def legacy_entity_registry_source_inputs(scope: ProjectScope) -> list[Path]:
    """Return canonical source inputs for the legacy registry compatibility view."""

    inputs: list[Path] = [scope.root / "PROJECT.yaml"]
    for relative in (
        Path("logical"),
        Path("physical"),
        Path("physical-system"),
        Path("physical-component"),
    ):
        base = scope.adr_dir / relative
        if not base.exists():
            continue
        inputs.extend(
            path.resolve()
            for path in sorted(base.glob("*.yaml"))
            if path.is_file() and not path.is_symlink()
        )
    return inputs
