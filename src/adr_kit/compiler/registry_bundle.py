"""Registry bundle assembly from ArchModel (authoring-time / migration parity).

Authoring authority: adr-architecture-kit validates and helps author ADRs.
Public cross-repo contracts remain owned by ste-spec. Do not treat this module as a
second authority for shared IR/evidence/admission schemas; it supports authoring-time
projection and migration parity only. See repo AUTHORING-SYSTEM.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

import yaml

from ..identity import UUIDV7_PATTERN
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
from ..models.v2_0 import (
    NormalizedEntityRegistryV2,
    NormalizedEntityV2,
    RelationshipRegistryV2,
    UnresolvedRegistryV2,
)
from ..models.v2_1 import (
    NormalizedEntityRegistryV21,
    RelationshipRegistryV21,
    UnresolvedRegistryV21,
)
from ..scope import ProjectScope
from .backend.projection import (
    PROJECTABLE_ENTITY_TYPES,
    project_entity,
    project_entity_v2,
    project_relationship,
    project_relationship_v2,
    is_projectable_entity,
    project_entity_v21,
    project_relationship_v21,
    project_unresolved,
)
from .diagnostics import DiagnosticLevel, DiagnosticLog
from .frontend.adr_access import is_logical_adr_source_ref
from .ir import ArchModel
from .passes import validate_bundle

BUNDLE_GENERATOR_ID = "adr-architecture-index"


@dataclass
class ArchitectureDiscoveryBundle:
    architecture_index: ArchitectureIndex
    entity_registry: NormalizedEntityRegistry | NormalizedEntityRegistryV2 | NormalizedEntityRegistryV21
    relationship_registry: RelationshipRegistry | RelationshipRegistryV2 | RelationshipRegistryV21
    unresolved_registry: UnresolvedRegistry | UnresolvedRegistryV2 | UnresolvedRegistryV21
    decision_registry: NormalizedEntityRegistry | NormalizedEntityRegistryV2 | NormalizedEntityRegistryV21
    capability_registry: NormalizedEntityRegistry | NormalizedEntityRegistryV2 | NormalizedEntityRegistryV21
    invariant_registry: NormalizedEntityRegistry | NormalizedEntityRegistryV2 | NormalizedEntityRegistryV21
    component_registry: NormalizedEntityRegistry | NormalizedEntityRegistryV2 | NormalizedEntityRegistryV21
    system_registry: NormalizedEntityRegistry | NormalizedEntityRegistryV2 | NormalizedEntityRegistryV21
    legacy_entity_registry: EntityRegistry


def render_bundle_yaml(model: Any) -> str:
    """Render a registry bundle model deterministically."""

    return yaml.safe_dump(
        model.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True
    )


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
    model_version: str = "1.1",
) -> ArchitectureDiscoveryBundle:
    """Assemble the discovery bundle directly from the compiler IR."""

    diagnostics = diagnostics or DiagnosticLog()
    generated_at = (
        generated_at
        or model.metadata.generated_at
        or datetime.now(timezone.utc).replace(microsecond=0)
    )

    if model_version == "2.1":
        return _assemble_registry_bundle_v21(
            model,
            coverage=coverage,
            namespace=namespace,
            generated_at=generated_at,
            diagnostics=diagnostics,
            generator_id=generator_id,
        )
    if model_version == "2.0":
        return _assemble_registry_bundle_v2(
            model,
            coverage=coverage,
            namespace=namespace,
            generated_at=generated_at,
            diagnostics=diagnostics,
            generator_id=generator_id,
        )

    projected_entities = [
        projected
        for entity in model.entities.values()
        if entity.entity_type in PROJECTABLE_ENTITY_TYPES
        and (projected := project_entity(entity, model.relationships)) is not None
    ]
    projected_relationships = [
        project_relationship(relationship) for relationship in model.relationships.values()
    ]
    projected_unresolved = [project_unresolved(item) for item in model.unresolved.values()]

    entity_registry = NormalizedEntityRegistry(
        entities=sorted(projected_entities, key=lambda item: item.id)
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
            [
                legacy
                for entity in entity_registry.entities
                if (legacy := _legacy_entity(entity)) is not None
            ],
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


def _assemble_registry_bundle_v2(
    model: ArchModel,
    *,
    coverage: SourceCoverageSummary,
    namespace: str,
    generated_at: datetime,
    diagnostics: DiagnosticLog,
    generator_id: str,
) -> ArchitectureDiscoveryBundle:
    """Assemble model 2.0 UUID registries from compiler IR."""

    projected_entities = [
        projected_entity
        for entity in model.entities.values()
        if entity.entity_type in PROJECTABLE_ENTITY_TYPES
        and (projected_entity := project_entity_v2(entity, model.relationships, namespace))
        is not None
    ]
    projected_relationships = [
        projected_relationship
        for relationship in model.relationships.values()
        if (projected_relationship := project_relationship_v2(relationship)) is not None
    ]
    projected_unresolved = [project_unresolved(item) for item in model.unresolved.values()]

    entity_registry = NormalizedEntityRegistryV2(
        entities=sorted(projected_entities, key=lambda item: item.id)
    )
    relationship_registry = RelationshipRegistryV2(
        relationships=sorted(projected_relationships, key=lambda item: item.relationship_id)
    )
    unresolved_registry = UnresolvedRegistryV2(
        unresolved=sorted(projected_unresolved, key=lambda item: item.id)
    )

    validation_entities_list: list[NormalizedEntity] = []
    for entity in model.entities.values():
        if entity.entity_type not in PROJECTABLE_ENTITY_TYPES:
            continue
        if not UUIDV7_PATTERN.match(entity.id):
            continue
        validation_projected = project_entity(entity, model.relationships)
        if validation_projected is not None:
            validation_entities_list.append(validation_projected)
    validation_entities = NormalizedEntityRegistry(entities=validation_entities_list)
    # Keep only relationships whose endpoints are UUID entities (external targets excluded).
    uuid_entity_ids = {entity.id for entity in validation_entities.entities}
    validation_relationships = RelationshipRegistry(
        relationships=[
            project_relationship(item)
            for item in model.relationships.values()
            if item.from_entity_id in uuid_entity_ids
            and (
                item.to_entity_id in uuid_entity_ids
                or item.metadata.get("target_scope") in {"external", "expectation"}
            )
        ]
    )
    validate_bundle(
        validation_entities,
        validation_relationships,
        UnresolvedRegistry(unresolved=projected_unresolved),
        diagnostics=diagnostics,
    )

    decision_registry = _filtered_v2(entity_registry, "decision")
    capability_registry = _filtered_v2(entity_registry, "capability")
    invariant_registry = _filtered_v2(entity_registry, "invariant")
    component_registry = _filtered_v2(entity_registry, "component")
    system_registry = _filtered_v2(entity_registry, "system")
    legacy_registry = EntityRegistry(
        entities=sorted(
            [
                legacy
                for entity in projected_entities
                if (legacy := _legacy_entity_from_v2(entity)) is not None
            ],
            key=lambda item: item.entity_id,
        )
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


def _assemble_registry_bundle_v21(
    model: ArchModel,
    *,
    coverage: SourceCoverageSummary,
    namespace: str,
    generated_at: datetime,
    diagnostics: DiagnosticLog,
    generator_id: str,
) -> ArchitectureDiscoveryBundle:
    """Assemble the explicit canonical/compatibility model 2.1 boundary."""

    projected_entities = [
        projected
        for entity in model.entities.values()
        if is_projectable_entity(entity)
        and (projected := project_entity_v21(entity, model.relationships, namespace)) is not None
    ]
    projected_relationships = [
        projected
        for relationship in model.relationships.values()
        if (projected := project_relationship_v21(relationship)) is not None
    ]
    projected_unresolved = [project_unresolved(item) for item in model.unresolved.values()]

    entity_registry = NormalizedEntityRegistryV21(
        entities=sorted(projected_entities, key=lambda item: item.id)
    )
    relationship_registry = RelationshipRegistryV21(
        relationships=sorted(
            projected_relationships,
            key=lambda item: (getattr(item, "id", None) or getattr(item, "relationship_id", "")),
        )
    )
    unresolved_registry = UnresolvedRegistryV21(
        unresolved=sorted(projected_unresolved, key=lambda item: item.id)
    )

    # Core validation remains on the existing validator surface.  The v2.1
    # models themselves enforce the canonical/compatibility identity boundary.
    decision_registry = _filtered_v21(entity_registry, "decision")
    capability_registry = _filtered_v21(entity_registry, "capability")
    invariant_registry = _filtered_v21(entity_registry, "invariant")
    component_registry = _filtered_v21(entity_registry, "component")
    system_registry = _filtered_v21(entity_registry, "system")
    legacy_registry = EntityRegistry(entities=[])
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
    return NormalizedEntityRegistry(
        entities=[entity for entity in registry.entities if entity.entity_type == entity_type]
    )


def _filtered_v2(
    registry: NormalizedEntityRegistryV2, entity_type: str
) -> NormalizedEntityRegistryV2:
    return NormalizedEntityRegistryV2(
        entities=[entity for entity in registry.entities if entity.entity_type == entity_type]
    )


def _filtered_v21(
    registry: NormalizedEntityRegistryV21, entity_type: str
) -> NormalizedEntityRegistryV21:
    return NormalizedEntityRegistryV21(
        entities=[entity for entity in registry.entities if entity.entity_type == entity_type]
    )


_LEGACY_ENTITY_ID_RE = re.compile(r"^[A-Z]+-\d{4}$")
_LEGACY_ADR_ID_RE = re.compile(r"^ADR-(L|V|P|PS|PC|D)-\d{4}$")


def _legacy_entity(entity: NormalizedEntity) -> Entity | None:
    mapping = {
        "capability": EntityType.CAPABILITY,
        "component": EntityType.COMPONENT,
        "decision": EntityType.DECISION,
        "invariant": EntityType.INVARIANT,
    }
    if entity.entity_type not in mapping:
        return None
    if entity.entity_type == "component" and entity.id != entity.metadata.get(
        "legacy_component_id", entity.id
    ):
        # Prefer alias_id path for UUID components below.
        if not UUIDV7_PATTERN.match(entity.id):
            return None

    entity_id = entity.id
    if UUIDV7_PATTERN.match(entity.id):
        alias_id = entity.metadata.get("alias_id")
        if not isinstance(alias_id, str) or not _LEGACY_ENTITY_ID_RE.match(alias_id):
            return None
        entity_id = alias_id
    elif not _LEGACY_ENTITY_ID_RE.match(entity_id):
        return None

    introduced_by = entity.canonical_source.source_ref.split("#")[0]
    source_type = SourceArtifactType.LOGICAL_ADR
    if introduced_by.startswith("ADR-PC-"):
        source_type = SourceArtifactType.PHYSICAL_COMPONENT_ADR
    elif introduced_by.startswith("ADR-PS-"):
        source_type = SourceArtifactType.PHYSICAL_SYSTEM_ADR
    elif UUIDV7_PATTERN.match(introduced_by):
        adr_alias = entity.metadata.get("adr_alias_id")
        source_type_name = entity.canonical_source.source_type
        if source_type_name == "physical_component_adr":
            source_type = SourceArtifactType.PHYSICAL_COMPONENT_ADR
        elif source_type_name == "physical_system_adr":
            source_type = SourceArtifactType.PHYSICAL_SYSTEM_ADR
        if not isinstance(adr_alias, str) or not _LEGACY_ADR_ID_RE.match(adr_alias):
            return None
        introduced_by = adr_alias
    elif not introduced_by.startswith("ADR-"):
        source_type = SourceArtifactType.STANDALONE_INVARIANT
        introduced_by = entity.metadata.get("defined_in") or "ADR-L-0001"

    related = set()
    for ref in entity.source_refs:
        owner = ref.source_ref.split("#")[0]
        if owner.startswith("ADR-") or is_logical_adr_source_ref(ref.source_ref):
            alias = entity.metadata.get("adr_alias_id") if UUIDV7_PATTERN.match(owner) else owner
            if isinstance(alias, str) and _LEGACY_ADR_ID_RE.match(alias):
                related.add(alias)
            elif owner.startswith("ADR-"):
                related.add(owner)

    return Entity(
        entity_id=entity_id,
        entity_type=mapping[entity.entity_type],
        name=entity.name,
        introduced_by=introduced_by,
        lifecycle_stage=LifecycleStage.ACTIVE,
        source_path=entity.canonical_source.artifact_path,
        source_artifact_type=source_type,
        related_adrs=sorted(related),
        relationships=EntityRelationships(
            depends_on=[
                item
                for item in entity.relationships.related_to
                if _LEGACY_ENTITY_ID_RE.match(item) or not UUIDV7_PATTERN.match(item)
            ],
            implements=[
                item
                for item in entity.relationships.enables
                if _LEGACY_ENTITY_ID_RE.match(item) or not UUIDV7_PATTERN.match(item)
            ],
            realizes=[
                item
                for item in entity.relationships.enforces
                if _LEGACY_ENTITY_ID_RE.match(item) or not UUIDV7_PATTERN.match(item)
            ],
        ),
    )


def _legacy_entity_from_v2(entity: NormalizedEntityV2) -> Entity | None:
    """Build a legacy Entity from a NormalizedEntityV2 using alias presentation IDs."""
    mapping = {
        "capability": EntityType.CAPABILITY,
        "component": EntityType.COMPONENT,
        "decision": EntityType.DECISION,
        "invariant": EntityType.INVARIANT,
    }
    if entity.entity_type not in mapping:
        return None
    if not _LEGACY_ENTITY_ID_RE.match(entity.alias_id):
        return None

    introduced_by = entity.canonical_source.source_ref.split("#")[0]
    source_type = SourceArtifactType.LOGICAL_ADR
    adr_alias = entity.metadata.get("adr_alias_id")
    if entity.canonical_source.source_type == "physical_component_adr":
        source_type = SourceArtifactType.PHYSICAL_COMPONENT_ADR
    elif entity.canonical_source.source_type == "physical_system_adr":
        source_type = SourceArtifactType.PHYSICAL_SYSTEM_ADR
    if UUIDV7_PATTERN.match(introduced_by):
        if not isinstance(adr_alias, str) or not _LEGACY_ADR_ID_RE.match(adr_alias):
            return None
        introduced_by = adr_alias
    elif not _LEGACY_ADR_ID_RE.match(introduced_by):
        return None

    return Entity(
        entity_id=entity.alias_id,
        entity_type=mapping[entity.entity_type],
        name=entity.name,
        introduced_by=introduced_by,
        lifecycle_stage=LifecycleStage.ACTIVE,
        source_path=entity.canonical_source.artifact_path,
        source_artifact_type=source_type,
        related_adrs=[introduced_by],
        relationships=EntityRelationships(),
    )
