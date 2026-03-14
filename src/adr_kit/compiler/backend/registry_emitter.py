"""Registry and index emission for the unified compiler driver."""

from __future__ import annotations

from pathlib import Path

from ...generators.architecture_index_generator import ArchitectureDiscoveryBundle, ArchitectureIndexGenerator
from ...integrity import (
    ArtifactKind,
    GENERATED_MARKER,
    HASH_ALGORITHM,
    INTEGRITY_SCHEMA_VERSION,
    LEGACY_ENTITY_REGISTRY_GENERATOR,
    build_yaml_header,
    compute_rendered_hash,
    compute_source_hash,
    legacy_entity_registry_source_inputs,
)
from ...scope import ProjectScope
from .common import EmittedArtifact


def emit_registry_artifacts(
    bundle: ArchitectureDiscoveryBundle,
    *,
    generator: ArchitectureIndexGenerator,
    scope: ProjectScope,
) -> list[EmittedArtifact]:
    """Serialize the architecture discovery bundle into compiler artifacts."""

    legacy_body = generator.render_yaml(bundle.legacy_entity_registry)
    legacy_header = build_yaml_header(
        {
            "integrity_schema_version": str(INTEGRITY_SCHEMA_VERSION),
            "generated": GENERATED_MARKER,
            "artifact_kind": ArtifactKind.LEGACY_ENTITY_REGISTRY.value,
            "generator_id": LEGACY_ENTITY_REGISTRY_GENERATOR.generator_id,
            "generator_version": str(LEGACY_ENTITY_REGISTRY_GENERATOR.generator_version),
            "hash_algorithm": HASH_ALGORITHM,
            "source_hash": compute_source_hash(
                scope.root,
                legacy_entity_registry_source_inputs(scope),
                LEGACY_ENTITY_REGISTRY_GENERATOR,
            ),
            "rendered_hash": compute_rendered_hash(legacy_body),
        }
    )
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
            content=generator.render_yaml(model).encode("utf-8"),
            kind=kind,
        )
        for relative_path, model, kind in payloads
    ]
    emitted.append(
        EmittedArtifact(
            path=Path("adrs/entities/registry.yaml"),
            content=f"{legacy_header}{legacy_body}".encode("utf-8"),
            kind="legacy",
            integrity_header=legacy_header,
        )
    )
    return emitted
