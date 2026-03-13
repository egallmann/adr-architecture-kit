"""Repository abstraction over generated architecture discovery artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from ..models import Entity, NormalizedEntity, RelationshipRecord
from ..parser import ADRParser
from ..scope import ProjectScopeResolver
from .registry_loader import (
    fingerprint_payload,
    load_architecture_index,
    load_legacy_entity_registry,
    load_normalized_entity_registry,
    load_relationship_registry,
    load_unresolved_registry,
    model_payload,
)
from .registry_paths import discover_repository_paths, resolve_index_reference


class ArchitectureRegistryError(Exception):
    """Deterministic repository loading failure."""


class ArchitectureRepository:
    """Load architecture discovery artifacts through one stable interface."""

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

    def get_entities(self) -> list[NormalizedEntity] | list[Entity]:
        self.load()
        return list(self._entities)

    def get_components(self) -> list[NormalizedEntity]:
        return self._get_subset("components")

    def get_capabilities(self) -> list[NormalizedEntity]:
        return self._get_subset("capabilities")

    def get_decisions(self) -> list[NormalizedEntity]:
        return self._get_subset("decisions")

    def get_invariants(self) -> list[NormalizedEntity]:
        return self._get_subset("invariants")

    def get_systems(self) -> list[NormalizedEntity]:
        return self._get_subset("systems")

    def get_relationships(self) -> list[RelationshipRecord]:
        self.load()
        return list(self._relationships)

    def find_entity(self, entity_id: str) -> NormalizedEntity | Entity | None:
        self.load()
        return self._entities_by_id.get(entity_id)

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
                "subset_registries": {
                    name: model_payload(model) for name, model in sorted(subset_models.items())
                },
            }
        )

    def _load_legacy(self, legacy_path: Path) -> None:
        legacy_registry = load_legacy_entity_registry(self._parser, legacy_path)
        self.architecture_index = None
        self.primary_entity_registry = None
        self.relationship_registry = None
        self.unresolved_registry = None
        self.legacy_entity_registry = legacy_registry
        self._entities = list(legacy_registry.entities)
        self._entities_by_id = {entity.entity_id: entity for entity in legacy_registry.entities}
        self._relationships = []
        self._subsets = {
            "components": [],
            "capabilities": [],
            "decisions": [],
            "invariants": [],
            "systems": [],
        }
        self._fingerprint = fingerprint_payload(
            {
                "mode": "legacy",
                "legacy_entity_registry": model_payload(legacy_registry),
            }
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
        self.legacy_entity_registry = None
        self._entities: list[NormalizedEntity] | list[Entity] = []
        self._entities_by_id: dict[str, NormalizedEntity | Entity] = {}
        self._relationships: list[RelationshipRecord] = []
        self._subsets: dict[str, list[NormalizedEntity]] = {
            "components": [],
            "capabilities": [],
            "decisions": [],
            "invariants": [],
            "systems": [],
        }
