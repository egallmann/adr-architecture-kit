"""Architecture Repository Boundary over compiled discovery artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..models import (
    ArchitectureIndex,
    DiscoveryProvenance,
    NormalizedArchitectureModel,
    NormalizedEntity,
    RemediationLedger,
    RelationshipRegistry,
    RelationshipRecord,
    SourceRef,
    UnresolvedRegistry,
    UnresolvedRecord,
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
from .semantic_adapter import coerce_to_normalized_model
from ..decorators import implements_adr


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


@implements_adr("ADR-L-0013")
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
            entities = [
                entity
                for entity in entities
                if adr in self.get_model().canonical_adr_refs_for_entity(entity.id)
            ]
        if domain:
            entities = [
                entity
                for entity in entities
                if domain in self.get_model().entity_domains(entity.id)
            ]
        if status:
            entities = [
                entity
                for entity in entities
                if self.get_model().entity_status(entity.id) == status
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

    @implements_adr("ADR-L-0013")
    def get_unresolved_by_role(
        self,
        entity_id: str,
        *,
        role: Literal["source", "related", "any"] = "source",
    ) -> list[UnresolvedRecord]:
        return self.get_model().unresolved_for_entity(entity_id, role=role)

    def get_adr_status(self, adr_id: str) -> str | None:
        return self.get_model().adr_status(adr_id)

    def get_entity_provenance(self, entity_id: str) -> DiscoveryProvenance | None:
        return self.get_model().provenance_for_entity(entity_id)

    @implements_adr("ADR-L-0013")
    def get_entity_canonical_source_ref(self, entity_id: str) -> str | None:
        return self.get_model().canonical_source_ref_for_entity(entity_id)

    @implements_adr("ADR-L-0013")
    def get_entity_source_refs(self, entity_id: str) -> list[SourceRef]:
        return self.get_model().source_refs_for_entity(entity_id)

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
        adapted_model = coerce_to_normalized_model(
            legacy_registry,
            fingerprint="legacy-architecture-repository",
            scope_root=str(self._scope_root) if self._scope_root else str(legacy_path.parent.parent),
            architecture_namespace=getattr(self._scope_resolver.resolve(), "name", None),
            generator="adr-architecture-repository",
            extraction_phase="architecture_repository.load_legacy",
        )
        self._entities = list(adapted_model.entities)
        self._entities_by_id = {entity.id: entity for entity in adapted_model.entities}
        self._relationships = list(adapted_model.relationships)
        self._subsets = {
            "components": [entity for entity in adapted_model.entities if entity.entity_type == "component"],
            "capabilities": [entity for entity in adapted_model.entities if entity.entity_type == "capability"],
            "decisions": [entity for entity in adapted_model.entities if entity.entity_type == "decision"],
            "invariants": [entity for entity in adapted_model.entities if entity.entity_type == "invariant"],
            "systems": [entity for entity in adapted_model.entities if entity.entity_type == "system"],
        }
        self._fingerprint = fingerprint_payload(
            {
                "mode": "legacy",
                "legacy_entity_registry": model_payload(legacy_registry),
            }
        )
        self._model = adapted_model.model_copy(update={"fingerprint": self._fingerprint})

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
