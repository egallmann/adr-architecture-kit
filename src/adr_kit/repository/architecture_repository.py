"""Architecture Repository Boundary over compiled discovery artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..models import (
    ArchitectureIndex,
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    Entity,
    NormalizedArchitectureModel,
    NormalizedEntity,
    RemediationLedger,
    RelationshipRegistry,
    RelationshipRecord,
    SourceCoverageSummary,
    SourceRef,
    UnresolvedRegistry,
    UnresolvedRecord,
    ValidationSummary,
)
from ..parser import ADRParser
from ..scope import ProjectScopeResolver
from .registry_loader import (
    fingerprint_payload,
    load_architecture_index,
    load_legacy_entity_registry,
    load_normalized_entity_registry,
    load_remediation_ledger,
    load_relationship_registry,
    load_unresolved_registry,
    model_payload,
)
from .registry_paths import discover_repository_paths, resolve_index_reference


class ArchitectureRegistryError(Exception):
    """Deterministic repository loading failure."""


@dataclass(frozen=True)
class ContractBundleView:
    """Repository-facing typed contract bundle for consumer workflows."""

    architecture_index: ArchitectureIndex
    entity_registry: object
    relationship_registry: RelationshipRegistry
    unresolved_registry: UnresolvedRegistry
    remediation_ledger: RemediationLedger | None


class ArchitectureRepository:
    """Load compiled bundles and expose a stable semantic model."""

    _SUBSET_TYPES: dict[str, tuple[str, str]] = {
        "component_registry_path": ("components", "component"),
        "capability_registry_path": ("capabilities", "capability"),
        "decision_registry_path": ("decisions", "decision"),
        "invariant_registry_path": ("invariants", "invariant"),
        "system_registry_path": ("systems", "system"),
    }

    def __init__(
        self,
        project_root: Path | None = None,
        scope_resolver: ProjectScopeResolver | None = None,
        parser: ADRParser | None = None,
    ) -> None:
        self._scope_resolver = scope_resolver or ProjectScopeResolver(explicit_scope=project_root)
        self._parser = parser or ADRParser()
        self.mode: Literal["normalized", "legacy"] | None = None
        self._loaded = False
        self._fingerprint: str | None = None
        self._reset_state()

    def load(self) -> None:
        """Load registry artifacts once."""
        if self._loaded:
            return
        self._load_fresh()

    def reload(self) -> None:
        """Force a disk refresh of repository state."""
        self._reset_state()
        self.mode = None
        self._loaded = False
        self._fingerprint = None
        self._load_fresh()

    def fingerprint(self) -> str:
        """Return the deterministic fingerprint of the loaded bundle."""
        self.load()
        if self._fingerprint is None:
            raise ArchitectureRegistryError("Repository fingerprint unavailable before successful load")
        return self._fingerprint

    def get_model(self) -> NormalizedArchitectureModel:
        """Return the normalized semantic boundary for the loaded scope."""

        self.load()
        if self._model is None:
            raise ArchitectureRegistryError("Normalized architecture model unavailable before successful load")
        return self._model

    def get_entities(self) -> list[NormalizedEntity]:
        self.load()
        return list(self.get_model().entities)

    def query_entities(
        self,
        *,
        entity_type: str | None = None,
        adr: str | None = None,
        domain: str | None = None,
        status: str | None = None,
    ) -> list[NormalizedEntity]:
        """Return deterministically filtered semantic entities."""

        entities = sorted(self.get_model().entities, key=lambda entity: entity.id)
        if entity_type:
            entities = [entity for entity in entities if entity.entity_type == entity_type]
        if adr:
            entities = [entity for entity in entities if adr in self._entity_adr_refs(entity)]
        if domain:
            entities = [
                entity
                for entity in entities
                if domain in ((entity.metadata or {}).get("domains", []) or [])
            ]
        if status:
            entities = [
                entity
                for entity in entities
                if ((entity.metadata or {}).get("status") == status)
            ]
        return entities

    def get_components(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="component")

    def get_capabilities(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="capability")

    def get_decisions(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="decision")

    def get_invariants(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="invariant")

    def get_systems(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="system")

    def get_relationships(self) -> list[RelationshipRecord]:
        self.load()
        return list(self.get_model().relationships)

    def get_relationships_for_entity(
        self,
        entity_id: str,
        *,
        relationship_type: str | None = None,
        direction: Literal["any", "incoming", "outgoing"] = "any",
    ) -> list[RelationshipRecord]:
        return self.get_model().relationships_for_entity(
            entity_id,
            relationship_type=relationship_type,
            direction=direction,
        )

    def get_unresolved_for_entity(self, entity_id: str) -> list[UnresolvedRecord]:
        return self.get_model().unresolved_for_entity(entity_id)

    def get_adr_status(self, adr_id: str) -> str | None:
        return self.get_model().adr_status(adr_id)

    def get_entity_provenance(self, entity_id: str) -> DiscoveryProvenance | None:
        return self.get_model().provenance_for_entity(entity_id)

    def get_entity_adr_refs(self, entity_id: str) -> list[str]:
        return self.get_model().canonical_adr_refs_for_entity(entity_id)

    def get_contract_bundle_view(self) -> ContractBundleView:
        """Return the compiled contract bundle through the repository boundary."""

        self.load()
        if self.mode != "normalized":
            raise ArchitectureRegistryError("Compiled contract bundle is unavailable in legacy repository mode")
        if (
            self.architecture_index is None
            or self.primary_entity_registry is None
            or self.relationship_registry is None
            or self.unresolved_registry is None
        ):
            raise ArchitectureRegistryError("Compiled contract bundle unavailable before successful normalized load")
        return ContractBundleView(
            architecture_index=self.architecture_index,
            entity_registry=self.primary_entity_registry,
            relationship_registry=self.relationship_registry,
            unresolved_registry=self.unresolved_registry,
            remediation_ledger=self.remediation_ledger,
        )

    def find_entity(self, entity_id: str) -> NormalizedEntity | None:
        self.load()
        return self.get_model().find_entity(entity_id)

    def _get_subset(self, name: str) -> list[NormalizedEntity]:
        self.load()
        return list(self._subsets.get(name, []))

    def _load_fresh(self) -> None:
        try:
            scope = self._scope_resolver.resolve()
            paths = discover_repository_paths(scope.root)
            self._scope_root = scope.root
            if paths.architecture_index.exists():
                self._load_normalized(paths.scope_root, paths.architecture_index)
                self.mode = "normalized"
            elif paths.legacy_entity_registry.exists():
                self._load_legacy(paths.legacy_entity_registry)
                self.mode = "legacy"
            else:
                raise ArchitectureRegistryError(
                    "Architecture discovery registry not found. "
                    "Run 'adr generate-architecture-index' or 'adr generate-entity-registry' first."
                )
            self._loaded = True
        except ArchitectureRegistryError:
            raise
        except Exception as exc:
            raise ArchitectureRegistryError(str(exc)) from exc

    def _load_normalized(self, scope_root: Path, index_path: Path) -> None:
        index = load_architecture_index(self._parser, index_path)
        primary_registry = load_normalized_entity_registry(
            self._parser,
            resolve_index_reference(scope_root, index.entity_registry_path),
        )
        relationship_registry = load_relationship_registry(
            self._parser,
            resolve_index_reference(scope_root, index.relationship_registry_path),
        )
        unresolved_registry = load_unresolved_registry(
            self._parser,
            resolve_index_reference(scope_root, index.unresolved_registry_path),
        )
        remediation_ledger = None
        remediation_ledger_path = discover_repository_paths(scope_root).remediation_ledger
        if remediation_ledger_path.exists():
            remediation_ledger = load_remediation_ledger(self._parser, remediation_ledger_path)
        primary_by_id = {entity.id: entity for entity in primary_registry.entities}
        subsets: dict[str, list[NormalizedEntity]] = {}
        subset_models: dict[str, object] = {}
        for field_name, (subset_name, expected_type) in self._SUBSET_TYPES.items():
            subset_path = resolve_index_reference(scope_root, getattr(index, field_name))
            subset_registry = load_normalized_entity_registry(self._parser, subset_path)
            self._validate_subset_registry(subset_registry, subset_name, expected_type, primary_by_id)
            subsets[subset_name] = list(subset_registry.entities)
            subset_models[subset_name] = subset_registry

        self.architecture_index = index
        self.primary_entity_registry = primary_registry
        self.relationship_registry = relationship_registry
        self.unresolved_registry = unresolved_registry
        self.remediation_ledger = remediation_ledger
        self.legacy_entity_registry = None
        self._entities = list(primary_registry.entities)
        self._entities_by_id = {entity.id: entity for entity in primary_registry.entities}
        self._relationships = list(relationship_registry.relationships)
        self._subsets = subsets
        self._fingerprint = fingerprint_payload(
            {
                "mode": "normalized",
                "architecture_index": model_payload(index),
                "entity_registry": model_payload(primary_registry),
                "relationship_registry": model_payload(relationship_registry),
                "unresolved_registry": model_payload(unresolved_registry),
                "remediation_ledger": model_payload(remediation_ledger),
                "subset_registries": {
                    name: model_payload(model) for name, model in sorted(subset_models.items())
                },
            }
        )
        self._model = NormalizedArchitectureModel(
            mode="normalized",
            scope_root=str(scope_root),
            architecture_namespace=index.architecture_namespace,
            fingerprint=self._fingerprint,
            entities=list(primary_registry.entities),
            relationships=list(relationship_registry.relationships),
            unresolved=list(unresolved_registry.unresolved),
            validation_summary=index.validation_summary,
            source_coverage=index.source_coverage,
        )

    def _load_legacy(self, legacy_path: Path) -> None:
        legacy_registry = load_legacy_entity_registry(self._parser, legacy_path)
        self.architecture_index = None
        self.primary_entity_registry = None
        self.relationship_registry = None
        self.unresolved_registry = None
        self.remediation_ledger = None
        self.legacy_entity_registry = legacy_registry
        adapted_entities = [self._legacy_entity_to_normalized(entity) for entity in legacy_registry.entities]
        adapted_relationships = self._legacy_relationships(adapted_entities)
        self._entities = adapted_entities
        self._entities_by_id = {entity.id: entity for entity in adapted_entities}
        self._relationships = adapted_relationships
        self._subsets = {
            "components": [entity for entity in adapted_entities if entity.entity_type == "component"],
            "capabilities": [entity for entity in adapted_entities if entity.entity_type == "capability"],
            "decisions": [entity for entity in adapted_entities if entity.entity_type == "decision"],
            "invariants": [entity for entity in adapted_entities if entity.entity_type == "invariant"],
            "systems": [entity for entity in adapted_entities if entity.entity_type == "system"],
        }
        self._fingerprint = fingerprint_payload(
            {
                "mode": "legacy",
                "legacy_entity_registry": model_payload(legacy_registry),
            }
        )
        self._model = NormalizedArchitectureModel(
            mode="legacy",
            scope_root=str(self._scope_root) if self._scope_root else str(legacy_path.parent.parent),
            architecture_namespace=getattr(self._scope_resolver.resolve(), "name", None),
            fingerprint=self._fingerprint,
            entities=adapted_entities,
            relationships=adapted_relationships,
            unresolved=[],
            validation_summary=ValidationSummary(
                hard_failures=0,
                warnings=0,
                unresolved_entries=0,
            ),
            source_coverage=None,
        )

    def _validate_subset_registry(
        self,
        subset_registry: object,
        subset_name: str,
        expected_type: str,
        primary_by_id: dict[str, NormalizedEntity],
    ) -> None:
        entities = getattr(subset_registry, "entities", None)
        if not isinstance(entities, list):
            raise ArchitectureRegistryError(f"Subset registry {subset_name} is malformed")
        for entity in entities:
            primary_entity = primary_by_id.get(entity.id)
            if primary_entity is None:
                raise ArchitectureRegistryError(
                    f"Subset registry {subset_name} references unknown entity ID: {entity.id}"
                )
            if entity.entity_type != expected_type:
                raise ArchitectureRegistryError(
                    f"Subset registry {subset_name} has mismatched entity_type for {entity.id}: "
                    f"expected {expected_type}, got {entity.entity_type}"
                )
            if entity.canonical_source.source_ref != primary_entity.canonical_source.source_ref:
                raise ArchitectureRegistryError(
                    f"Subset registry {subset_name} has mismatched canonical_source.source_ref for {entity.id}"
                )

    def _reset_state(self) -> None:
        self._scope_root: Path | None = None
        self.architecture_index = None
        self.primary_entity_registry = None
        self.relationship_registry = None
        self.unresolved_registry = None
        self.remediation_ledger = None
        self.legacy_entity_registry = None
        self._model: NormalizedArchitectureModel | None = None
        self._entities: list[NormalizedEntity] = []
        self._entities_by_id: dict[str, NormalizedEntity] = {}
        self._relationships: list[RelationshipRecord] = []
        self._subsets: dict[str, list[NormalizedEntity]] = {
            "components": [],
            "capabilities": [],
            "decisions": [],
            "invariants": [],
            "systems": [],
        }

    def _legacy_entity_to_normalized(self, entity: Entity) -> NormalizedEntity:
        entity_type = entity.entity_type.value
        if entity_type == "implementation_decision":
            entity_type = "decision"
        canonical_ref = f"{entity.introduced_by}#{entity.entity_id}"
        metadata = {
            "status": entity.lifecycle_stage.value,
            "domains": list(entity.domains or []),
            "legacy_source_artifact_type": entity.source_artifact_type.value,
            "introduced_by": entity.introduced_by,
        }
        if entity.ownership is not None:
            metadata["ownership"] = entity.ownership.model_dump(mode="json", exclude_none=True)

        relationships = getattr(entity, "relationships", None)
        related_to = list(getattr(relationships, "depends_on", []) or [])
        enables = list(getattr(relationships, "implements", []) or [])
        enforces = list(getattr(relationships, "realizes", []) or [])

        source_refs = [
            SourceRef(
                source_type="legacy_related_adr",
                source_ref=ref,
                artifact_path=entity.source_path,
                mention_role="reference",
            )
            for ref in sorted(
                {
                    *list(entity.related_adrs or []),
                    *list(entity.realized_by or []),
                }
            )
            if ref.startswith("ADR-")
        ]

        return NormalizedEntity(
            id=entity.entity_id,
            entity_type=entity_type,
            name=entity.name,
            summary=entity.name,
            canonical_source=CanonicalSource(
                source_type=entity.source_artifact_type.value,
                source_ref=canonical_ref,
                artifact_path=entity.source_path,
            ),
            source_refs=source_refs,
            metadata=metadata,
            relationships={
                "declared_in": [entity.introduced_by],
                "related_to": related_to,
                "enables": enables,
                "enforces": enforces,
            },
            completeness=Completeness(status="partial", missing_fields=["legacy_normalized_semantics"]),
            provenance=DiscoveryProvenance(
                source_type="legacy_entity_registry",
                source_ref=f"adrs/entities/registry.yaml#{entity.entity_id}",
                extraction_phase="architecture_repository.load_legacy",
                classification="derived",
                generator="adr-architecture-repository",
            ),
        )

    def _legacy_relationships(self, entities: list[NormalizedEntity]) -> list[RelationshipRecord]:
        relationships: list[RelationshipRecord] = []
        known_ids = {entity.id for entity in entities}

        for entity in entities:
            relationships.extend(
                self._relationship_records_for_targets(
                    entity=entity,
                    relationship_type="declared_in",
                    targets=list(entity.relationships.declared_in),
                    canonical_source_ref=entity.canonical_source.source_ref,
                    known_ids=known_ids,
                )
            )
            relationships.extend(
                self._relationship_records_for_targets(
                    entity=entity,
                    relationship_type="related_to",
                    targets=list(entity.relationships.related_to),
                    canonical_source_ref=entity.canonical_source.source_ref,
                    known_ids=known_ids,
                )
            )
            relationships.extend(
                self._relationship_records_for_targets(
                    entity=entity,
                    relationship_type="enables",
                    targets=list(entity.relationships.enables),
                    canonical_source_ref=entity.canonical_source.source_ref,
                    known_ids=known_ids,
                )
            )
            relationships.extend(
                self._relationship_records_for_targets(
                    entity=entity,
                    relationship_type="enforces",
                    targets=list(entity.relationships.enforces),
                    canonical_source_ref=entity.canonical_source.source_ref,
                    known_ids=known_ids,
                )
            )

        return sorted(relationships, key=lambda item: item.relationship_id)

    def _relationship_records_for_targets(
        self,
        *,
        entity: NormalizedEntity,
        relationship_type: str,
        targets: list[str],
        canonical_source_ref: str,
        known_ids: set[str],
    ) -> list[RelationshipRecord]:
        records: list[RelationshipRecord] = []
        for target in sorted(set(targets)):
            if target not in known_ids and not target.startswith("ADR-"):
                continue
            records.append(
                RelationshipRecord(
                    relationship_id=f"{relationship_type}:{entity.id}:{target}",
                    relationship_type=relationship_type,
                    from_entity_id=entity.id,
                    to_entity_id=target,
                    provenance_classification="derived",
                    evidence=[f"Adapted from legacy entity registry for {entity.id}"],
                    canonical_source_ref=canonical_source_ref,
                    confidence=1.0,
                )
            )
        return records

    def _entity_adr_refs(self, entity: NormalizedEntity) -> set[str]:
        refs = set()
        canonical_ref = entity.canonical_source.source_ref.split("#")[0]
        if canonical_ref.startswith("ADR-"):
            refs.add(canonical_ref)
        refs.update(
            ref.source_ref.split("#")[0]
            for ref in entity.source_refs
            if ref.source_ref.startswith("ADR-")
        )
        for metadata_ref_key in ("adr_id", "defined_in", "introduced_by"):
            metadata_ref = (entity.metadata or {}).get(metadata_ref_key)
            if isinstance(metadata_ref, str) and metadata_ref.startswith("ADR-"):
                refs.add(metadata_ref)
        refs.update(item for item in entity.relationships.declared_in if item.startswith("ADR-"))
        return refs
