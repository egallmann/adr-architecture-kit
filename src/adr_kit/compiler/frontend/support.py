"""Shared frontend support utilities for compiler and compatibility layers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...models import CanonicalSource, Completeness, DiscoveryProvenance
from ...scope import ProjectScope
from ..passes.score_completeness import score_completeness

GENERATOR_ID = "adr-architecture-index"


def discover_source_files(adr_dir: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Discover logical, physical, and invariant ADR sources deterministically."""
    logical = sorted((adr_dir / "logical").glob("*.yaml")) if (adr_dir / "logical").exists() else []
    physical: list[Path] = []
    for dirname in ("physical", "physical-system", "physical-component"):
        base = adr_dir / dirname
        if base.exists():
            physical.extend(sorted(base.glob("*.yaml")))
    invariants = sorted((adr_dir / "invariants").glob("*.yaml")) if (adr_dir / "invariants").exists() else []
    deduped = list(dict.fromkeys(path.resolve() for path in physical))
    return logical, [Path(path) for path in deduped], invariants


def source_path(scope: ProjectScope, file_path: Path) -> str:
    """Return a deterministic scope-relative source path."""
    return str(file_path.resolve().relative_to(scope.root.resolve())).replace("\\", "/")


def load_namespace(parser, scope: ProjectScope) -> str:
    """Load the authoritative architecture namespace for a scope."""
    data = parser.parse_yaml(scope.root / "PROJECT.yaml")
    namespace = ((data.get("architecture_documentation") or {}).get("architecture_namespace"))
    if not namespace:
        raise ValueError("PROJECT.yaml is missing architecture_documentation.architecture_namespace")
    return namespace


def make_provenance(source_type: str, source_ref: str, phase: str, classification: str) -> DiscoveryProvenance:
    """Build deterministic provenance metadata."""
    return DiscoveryProvenance(
        source_type=source_type,
        source_ref=source_ref,
        extraction_phase=phase,
        classification=classification,
        generator=GENERATOR_ID,
    )


def make_canonical(source_type: str, source_ref: str, artifact_path: str) -> CanonicalSource:
    """Build canonical source metadata."""
    return CanonicalSource(source_type=source_type, source_ref=source_ref, artifact_path=artifact_path)


def make_completeness(missing_fields: Optional[list[str]] = None) -> Completeness:
    """Build completeness metadata using current compiler semantics."""
    return score_completeness(missing_fields)


def summarize_text(text: str, limit: int = 220) -> str:
    """Create the deterministic short summary used in discovery output."""
    return " ".join((text or "").split())[:limit]


def classify_author_gap(gap) -> str:
    """Classify an author-declared ADR gap using current semantics."""
    context = (getattr(gap, "context", None) or "").lower()
    if "classification: deferred" in context:
        return "author_declared_deferred_gap"
    if "classification: resolved" in context:
        return "author_declared_resolved_gap"
    return "author_declared_real_gap"


def system_entity_id(adr_id: str) -> str:
    """Derive the canonical system entity ID from a physical-system ADR ID."""
    return f"SYS-{adr_id.replace('ADR-PS-', '')}"
