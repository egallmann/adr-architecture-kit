"""Registry and index emission for the unified compiler driver."""

from __future__ import annotations

from pathlib import Path

from ...generators.architecture_index_generator import ArchitectureDiscoveryBundle, ArchitectureIndexGenerator
from ...scope import ProjectScope
from .common import EmittedArtifact


def emit_registry_artifacts(
    bundle: ArchitectureDiscoveryBundle,
    *,
    generator: ArchitectureIndexGenerator,
    scope: ProjectScope,
) -> list[EmittedArtifact]:
    """Serialize the architecture discovery bundle into compiler artifacts."""

    payloads = [
        ("adrs/index/architecture-index.yaml", bundle.architecture_index, "index"),
        ("adrs/index/entity-registry.yaml", bundle.entity_registry, "registry"),
        ("adrs/index/relationship-registry.yaml", bundle.relationship_registry, "registry"),
        ("adrs/index/unresolved-registry.yaml", bundle.unresolved_registry, "registry"),
        ("adrs/index/decision-registry.yaml", bundle.decision_registry, "registry"),
        ("adrs/index/capability-registry.yaml", bundle.capability_registry, "registry"),
        ("adrs/index/invariant-registry.yaml", bundle.invariant_registry, "registry"),
        ("adrs/index/component-registry.yaml", bundle.component_registry, "registry"),
        ("adrs/index/system-registry.yaml", bundle.system_registry, "registry"),
        ("adrs/entities/registry.yaml", bundle.legacy_entity_registry, "legacy"),
    ]

    return [
        EmittedArtifact(
            path=Path(relative_path),
            content=generator.render_yaml(model).encode("utf-8"),
            kind=kind,
        )
        for relative_path, model, kind in payloads
    ]
