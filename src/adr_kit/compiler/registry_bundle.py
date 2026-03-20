"""Registry bundle assembly from ArchModel (authoring-time / migration parity).

Authoring authority: adr-architecture-kit validates and helps author ADRs.
Compiler authority: ste-runtime is the compiler of record for machine-consumable
architecture state for the runtime/kernel. Do not treat this module as the long-term
authoritative producer of runtime registry bundles—migrate projection to ste-runtime
and remove dual compilation. See repo AUTHORING-SYSTEM.md and ste-runtime COMPILER-AUTHORITY.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import yaml

from ..integrity import (
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
from ..models import (
    ArchitectureIndex,
    Entity,
    EntityRegistry,
    EntityRelationships,
    EntityType,
    LifecycleStage,
    NormalizedEntity,
    NormalizedEntityRegistry,
    RelationshipRegistry,
    SourceArtifactType,
    SourceCoverageSummary,
    UnresolvedRegistry,
    ValidationSummary,
)
from ..scope import ProjectScope
from .backend.projection import PROJECTABLE_ENTITY_TYPES, project_entity, project_relationship, project_unresolved
from .diagnostics import DiagnosticLevel, DiagnosticLog
from .ir import ArchModel
from .passes import validate_bundle


BUNDLE_GENERATOR_ID = "adr-architecture-index"


@dataclass
class ArchitectureDiscoveryBundle:
    architecture_index: ArchitectureIndex
    entity_registry: NormalizedEntityRegistry
    relationship_registry: RelationshipRegistry
    unresolved_registry: UnresolvedRegistry
    decision_registry: NormalizedEntityRegistry
    capability_registry: NormalizedEntityRegistry
    invariant_registry: NormalizedEntityRegistry
    component_registry: NormalizedEntityRegistry
    system_registry: NormalizedEntityRegistry
    legacy_entity_registry: EntityRegistry


def render_bundle_yaml(model) -> str:
    """Render a registry bundle model deterministically."""

    return yaml.safe_dump(model.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True)


def render_legacy_entity_registry(bundle: ArchitectureDiscoveryBundle, scope: ProjectScope) -> str:
    """Render the legacy compatibility registry with an integrity header."""

    body = render_bundle_yaml(bundle.legacy_entity_registry)
    header = build_yaml_header(
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
            "rendered_hash": compute_rendered_hash(body),
        }
    )
    return f"{header}{body}"


def assemble_registry_bundle(
    model: ArchModel,
    *,
    coverage: SourceCoverageSummary,
    namespace: str,
    generated_at: datetime | None = None,
    diagnostics: DiagnosticLog | None = None,
    generator_id: str = BUNDLE_GENERATOR_ID,
) -> ArchitectureDiscoveryBundle:
    """Assemble the discovery bundle directly from the compiler IR."""

    diagnostics = diagnostics or DiagnosticLog()
    generated_at = generated_at or model.metadata.generated_at or datetime.now(timezone.utc).replace(microsecond=0)

    projected_entities = [
        projected
        for entity in model.entities.values()
        if entity.entity_type in PROJECTABLE_ENTITY_TYPES
        and (projected := project_entity(entity, model.relationships)) is not None
    ]
    projected_relationships = [project_relationship(relationship) for relationship in model.relationships.values()]
    projected_unresolved = [project_unresolved(item) for item in model.unresolved.values()]

    entity_registry = NormalizedEntityRegistry(
        entities=sorted(projected_entities, key=lambda item: (item.entity_type, item.id))
    )
    relationship_registry = RelationshipRegistry(
        relationships=sorted(projected_relationships, key=lambda item: item.relationship_id)
    )
    unresolved_registry = UnresolvedRegistry(
        unresolved=sorted(projected_unresolved, key=lambda item: item.id)
    )
    decision_registry = _filtered(entity_registry, "decision")
    capability_registry = _filtered(entity_registry, "capability")
    invariant_registry = _filtered(entity_registry, "invariant")
    component_registry = _filtered(entity_registry, "component")
    system_registry = _filtered(entity_registry, "system")
    legacy_registry = EntityRegistry(
        entities=sorted(
            [legacy for entity in entity_registry.entities if (legacy := _legacy_entity(entity)) is not None],
            key=lambda item: item.entity_id,
        )
    )

    validate_bundle(
        entity_registry,
        relationship_registry,
        unresolved_registry,
        diagnostics=diagnostics,
    )
    hard_failures = sum(1 for item in diagnostics.as_list() if item.level == DiagnosticLevel.ERROR)
    warnings = sum(1 for item in diagnostics.as_list() if item.level == DiagnosticLevel.WARNING)

    index = ArchitectureIndex(
        architecture_namespace=namespace,
        generated_at=generated_at,
        generator=generator_id,
        entity_registry_path="adrs/index/entity-registry.yaml",
        relationship_registry_path="adrs/index/relationship-registry.yaml",
        unresolved_registry_path="adrs/index/unresolved-registry.yaml",
        decision_registry_path="adrs/index/decision-registry.yaml",
        capability_registry_path="adrs/index/capability-registry.yaml",
        invariant_registry_path="adrs/index/invariant-registry.yaml",
        component_registry_path="adrs/index/component-registry.yaml",
        system_registry_path="adrs/index/system-registry.yaml",
        validation_summary=ValidationSummary(
            hard_failures=hard_failures,
            warnings=warnings,
            unresolved_entries=len(unresolved_registry.unresolved),
        ),
        source_coverage=coverage,
    )
    return ArchitectureDiscoveryBundle(
        architecture_index=index,
        entity_registry=entity_registry,
        relationship_registry=relationship_registry,
        unresolved_registry=unresolved_registry,
        decision_registry=decision_registry,
        capability_registry=capability_registry,
        invariant_registry=invariant_registry,
        component_registry=component_registry,
        system_registry=system_registry,
        legacy_entity_registry=legacy_registry,
    )


def _filtered(registry: NormalizedEntityRegistry, entity_type: str) -> NormalizedEntityRegistry:
    return NormalizedEntityRegistry(entities=[entity for entity in registry.entities if entity.entity_type == entity_type])


def _legacy_entity(entity: NormalizedEntity) -> Entity | None:
    mapping = {
        "capability": EntityType.CAPABILITY,
        "component": EntityType.COMPONENT,
        "decision": EntityType.DECISION,
        "invariant": EntityType.INVARIANT,
    }
    if entity.entity_type not in mapping:
        return None
    if entity.entity_type == "component" and entity.id != entity.metadata.get("legacy_component_id", entity.id):
        return None

    introduced_by = entity.canonical_source.source_ref.split("#")[0]
    source_type = SourceArtifactType.LOGICAL_ADR
    if introduced_by.startswith("ADR-PC-"):
        source_type = SourceArtifactType.PHYSICAL_COMPONENT_ADR
    elif introduced_by.startswith("ADR-PS-"):
        source_type = SourceArtifactType.PHYSICAL_SYSTEM_ADR
    elif not introduced_by.startswith("ADR-"):
        source_type = SourceArtifactType.STANDALONE_INVARIANT
        introduced_by = entity.metadata.get("defined_in") or "ADR-L-0001"

    return Entity(
        entity_id=entity.id,
        entity_type=mapping[entity.entity_type],
        name=entity.name,
        introduced_by=introduced_by,
        lifecycle_stage=LifecycleStage.ACTIVE,
        source_path=entity.canonical_source.artifact_path,
        source_artifact_type=source_type,
        related_adrs=sorted(
            {
                ref.source_ref.split("#")[0]
                for ref in entity.source_refs
                if ref.source_ref.startswith("ADR-")
            }
        ),
        relationships=EntityRelationships(
            depends_on=list(entity.relationships.related_to),
            implements=list(entity.relationships.enables),
            realizes=list(entity.relationships.enforces),
        ),
    )
