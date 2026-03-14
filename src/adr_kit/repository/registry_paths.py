"""Scope-safe registry path discovery for architecture repositories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..pathing import ensure_within_scope


@dataclass(frozen=True)
class RepositoryPaths:
    """Canonical discovery locations for repository loading."""

    scope_root: Path
    architecture_index: Path
    legacy_entity_registry: Path
    remediation_ledger: Path


def discover_repository_paths(scope_root: Path) -> RepositoryPaths:
    """Return canonical repository entrypoints for a resolved scope."""
    root = Path(scope_root).resolve()
    return RepositoryPaths(
        scope_root=root,
        architecture_index=root / "adrs" / "index" / "architecture-index.yaml",
        legacy_entity_registry=root / "adrs" / "entities" / "registry.yaml",
        remediation_ledger=root / "adrs" / "governance" / "remediation-ledger.yaml",
    )


def resolve_index_reference(scope_root: Path, relative_path: str) -> Path:
    """Resolve an index-referenced path and ensure it stays within the scope root."""
    root = Path(scope_root).resolve()
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"Index-referenced path must be relative to scope root: {relative_path}")
    try:
        return ensure_within_scope(root, root / candidate)
    except ValueError as exc:
        raise ValueError(f"Index-referenced path escapes scope root: {relative_path}") from exc
