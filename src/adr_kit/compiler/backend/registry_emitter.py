"""Registry and index emission for the unified compiler driver."""

from __future__ import annotations

from pathlib import Path

from ...decorators import implements_adr
from ..registry_bundle import ArchitectureDiscoveryBundle, render_bundle_yaml, render_legacy_entity_registry
from ...scope import ProjectScope
from .common import EmittedArtifact


@implements_adr("ADR-L-0009", "ADR-L-0010", "ADR-PC-0003")
def emit_registry_artifacts(
    bundle: ArchitectureDiscoveryBundle,
    *,
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
    ]

    emitted = [
        EmittedArtifact(
            path=Path(relative_path),
            content=render_bundle_yaml(model).encode("utf-8"),
            kind=kind,
        )
        for relative_path, model, kind in payloads
    ]
    legacy_content = render_legacy_entity_registry(bundle, scope)
    header, _, _ = legacy_content.partition("\n\n")
    header = header + "\n\n"
    emitted.append(
        EmittedArtifact(
            path=Path("adrs/entities/registry.yaml"),
            content=legacy_content.encode("utf-8"),
            kind="legacy",
            integrity_header=header,
        )
    )
    return emitted
