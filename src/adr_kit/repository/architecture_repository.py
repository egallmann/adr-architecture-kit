"""Architecture Repository Boundary over compiled discovery artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
import re
import yaml

from ..models import (
    ArchitectureIndex,
    CorpusSummary,
    DiscoveryProvenance,
    EntityRegistry,
    Manifest,
    NormalizedArchitectureModel,
    NormalizedEntity,
    NormalizedEntityRegistry,
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
    load_legacy_entity_registry,
    model_payload,
)
from .registry_paths import discover_repository_paths
from ._normalized_bundle import SUBSET_TYPES, load_normalized_bundle_from_paths
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


@dataclass(frozen=True)
class AdrIdAllocationBands:
    """Centralized ADR allocation band policy."""

    normal_start: int = 1
    normal_end: int = 8999
    reserved_start: int = 9000
    reserved_end: int = 9999


@implements_adr("ADR-L-0013")
class ArchitectureRepository:
    """Load compiled bundles and expose a stable semantic model."""

    _scope_root: Path | None
    architecture_index: ArchitectureIndex | None
    primary_entity_registry: NormalizedEntityRegistry | None
    relationship_registry: RelationshipRegistry | None
    unresolved_registry: UnresolvedRegistry | None
    remediation_ledger: RemediationLedger | None
    legacy_entity_registry: EntityRegistry | None
    _model: NormalizedArchitectureModel | None
    _entities: list[NormalizedEntity]
    _entities_by_id: dict[str, NormalizedEntity]
    _relationships: list[RelationshipRecord]
    _subsets: dict[str, list[NormalizedEntity]]

    _SUBSET_TYPES = SUBSET_TYPES
    _ADR_TYPE_PATTERNS: dict[str, tuple[str, str]] = {
        "logical": ("ADR-L-", "logical"),
        "physical-system": ("ADR-PS-", "physical-system"),
        "physical-component": ("ADR-PC-", "physical-component"),
    }
    _ADR_ID_BANDS = AdrIdAllocationBands()
    _ALLOCATION_STATE_FILE = ".adr-id-allocation.yaml"

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
            raise ArchitectureRegistryError(
                "Repository fingerprint unavailable before successful load"
            )
        return self._fingerprint

    def get_model(self) -> NormalizedArchitectureModel:
        """Return the normalized semantic boundary for the loaded scope."""

        self.load()
        if self._model is None:
            raise ArchitectureRegistryError(
                "Normalized architecture model unavailable before successful load"
            )
        return self._model

    def get_manifest(self) -> Manifest:
        """Return the parsed manifest for the current scope."""
        scope = self._scope_resolver.resolve()
        if not scope.manifest_path.exists():
            raise ArchitectureRegistryError(
                f"Manifest not found for scope {scope.root}. Run 'adr generate-manifest' or 'adr compile' first."
            )
        try:
            return Manifest(**self._parser.parse_yaml(scope.manifest_path))
        except Exception as exc:
            raise ArchitectureRegistryError(f"Failed to load manifest: {exc}") from exc

    def get_index(self) -> ArchitectureIndex:
        """Return the architecture index for normalized repository mode."""
        self.load()
        if self.mode != "normalized" or self.architecture_index is None:
            raise ArchitectureRegistryError(
                "Architecture index is unavailable in legacy repository mode"
            )
        return self.architecture_index

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
                entity for entity in entities if self.get_model().entity_status(entity.id) == status
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

    def get_boundaries(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="boundary")

    def get_contracts(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="contract")

    def get_interfaces(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="interface")

    def get_implementation_decisions(self) -> list[NormalizedEntity]:
        return self.query_entities(entity_type="implementation_decision")

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

    def find_adrs_referencing_entity(self, entity_id: str) -> list[str]:
        """Return ADR IDs directly associated to an entity through repository relationships."""
        self.load()
        if self.find_entity(entity_id) is None:
            raise ArchitectureRegistryError(f"Entity not found: {entity_id}")

        references: set[str] = set(self.get_entity_adr_refs(entity_id))
        for relationship in self.get_relationships_for_entity(entity_id):
            for candidate_id in (relationship.from_entity_id, relationship.to_entity_id):
                if candidate_id == entity_id:
                    continue
                candidate = self.find_entity(candidate_id)
                if candidate is None:
                    continue
                if candidate.entity_type == "adr":
                    references.add(candidate.id)
                references.update(self.get_entity_adr_refs(candidate_id))
        return sorted(references)

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
            raise ArchitectureRegistryError(
                "Compiled contract bundle is unavailable in legacy repository mode"
            )
        if (
            self.architecture_index is None
            or self.primary_entity_registry is None
            or self.relationship_registry is None
            or self.unresolved_registry is None
        ):
            raise ArchitectureRegistryError(
                "Compiled contract bundle unavailable before successful normalized load"
            )
        return ContractBundleView(
            architecture_index=self.architecture_index,
            entity_registry=self.primary_entity_registry,
            relationship_registry=self.relationship_registry,
            unresolved_registry=self.unresolved_registry,
            remediation_ledger=self.remediation_ledger,
        )

    def get_corpus_summary(self) -> CorpusSummary:
        """Return deterministic corpus orientation data for the current scope."""
        model = self.get_model()
        entity_counts: dict[str, int] = {}
        adr_counts_by_type: dict[str, int] = {}
        adr_counts_by_status: dict[str, int] = {}

        for entity in model.entities:
            entity_counts[entity.entity_type] = entity_counts.get(entity.entity_type, 0) + 1
            if entity.entity_type != "adr":
                continue
            adr_type = self._adr_type_for_id(entity.id)
            adr_counts_by_type[adr_type] = adr_counts_by_type.get(adr_type, 0) + 1
            adr_status = model.adr_status(entity.id) or "unknown"
            adr_counts_by_status[adr_status] = adr_counts_by_status.get(adr_status, 0) + 1

        return CorpusSummary(
            scope_root=model.scope_root,
            architecture_namespace=model.architecture_namespace,
            fingerprint=model.fingerprint,
            mode=model.mode,
            entity_counts=dict(sorted(entity_counts.items())),
            adr_counts_by_type=dict(sorted(adr_counts_by_type.items())),
            adr_counts_by_status=dict(sorted(adr_counts_by_status.items())),
            relationship_count=len(model.relationships),
            unresolved_count=len(model.unresolved),
            source_coverage=model.source_coverage,
            validation_summary=model.validation_summary,
        )

    def _adr_type_for_id(self, adr_id: str) -> str:
        """Infer ADR taxonomy from canonical ADR ID."""
        if adr_id.startswith("ADR-L-") or adr_id.startswith("ADR-V-"):
            return "logical"
        if adr_id.startswith("ADR-PS-"):
            return "physical-system"
        if adr_id.startswith("ADR-PC-"):
            return "physical-component"
        if adr_id.startswith("ADR-P-"):
            return "physical"
        return "unknown"

    def next_id(self, adr_type: str) -> str:
        """Allocate the next normal-band ADR ID for a supported forward-authoring type."""
        if adr_type not in self._ADR_TYPE_PATTERNS:
            allowed = ", ".join(sorted(self._ADR_TYPE_PATTERNS))
            raise ArchitectureRegistryError(
                f"Unsupported ADR type for next-id: {adr_type}. Expected one of: {allowed}"
            )

        prefix, directory_name = self._ADR_TYPE_PATTERNS[adr_type]
        scope = self._scope_resolver.resolve()
        target_dir = scope.adr_dir / directory_name
        pattern = re.compile(rf"^{re.escape(prefix)}(\d{{4}})")

        highest = self._load_allocation_high_water(scope.root, adr_type)
        seen_ids: dict[str, Path] = {}
        if target_dir.exists():
            for path in sorted(target_dir.glob("*.yaml")):
                try:
                    data = self._parser.parse_yaml(path)
                except Exception as exc:
                    raise ArchitectureRegistryError(
                        f"Failed to read ADR header from {path}: {exc}"
                    ) from exc

                declared_id = data.get("id")
                if not isinstance(declared_id, str):
                    continue

                existing_path = seen_ids.get(declared_id)
                if existing_path is not None:
                    raise ArchitectureRegistryError(
                        f"Duplicate ADR ID in {target_dir}: {declared_id} declared in both {existing_path.name} and {path.name}"
                    )
                seen_ids[declared_id] = path

                match = pattern.match(declared_id)
                if match:
                    sequence = int(match.group(1))
                    if self._ADR_ID_BANDS.normal_start <= sequence <= self._ADR_ID_BANDS.normal_end:
                        highest = max(highest, sequence)

        next_sequence = highest + 1
        if next_sequence > self._ADR_ID_BANDS.normal_end:
            raise ArchitectureRegistryError(
                f"ADR ID allocation band exhausted for {adr_type}: "
                f"{self._ADR_ID_BANDS.normal_start:04d}-{self._ADR_ID_BANDS.normal_end:04d}"
            )

        self._save_allocation_high_water(scope.root, adr_type, next_sequence)
        return f"{prefix}{next_sequence:04d}"

    def _allocation_state_path(self, scope_root: Path) -> Path:
        """Return the repo-local ADR allocation state file path."""
        return scope_root / self._ALLOCATION_STATE_FILE

    def _load_allocation_high_water(self, scope_root: Path, adr_type: str) -> int:
        """Load the current high-water mark for an ADR type."""
        state_path = self._allocation_state_path(scope_root)
        if not state_path.exists():
            return 0
        try:
            data = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise ArchitectureRegistryError(
                f"Failed to load ADR allocation state from {state_path}: {exc}"
            ) from exc

        allocation = data.get("allocation", {})
        value = allocation.get(adr_type, 0)
        if not isinstance(value, int):
            raise ArchitectureRegistryError(
                f"Invalid ADR allocation state for {adr_type} in {state_path}"
            )
        return value

    def _save_allocation_high_water(self, scope_root: Path, adr_type: str, high_water: int) -> None:
        """Persist the current high-water mark for an ADR type."""
        state_path = self._allocation_state_path(scope_root)
        data: dict[str, Any] = {}
        if state_path.exists():
            try:
                data = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                raise ArchitectureRegistryError(
                    f"Failed to load ADR allocation state from {state_path}: {exc}"
                ) from exc
        allocation = data.setdefault("allocation", {})
        existing = allocation.get(adr_type, 0)
        if not isinstance(existing, int):
            raise ArchitectureRegistryError(
                f"Invalid ADR allocation state for {adr_type} in {state_path}"
            )
        allocation[adr_type] = max(existing, high_water)
        state_path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
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
        bundle = load_normalized_bundle_from_paths(self._parser, scope_root, index_path)
        self.architecture_index = bundle.architecture_index
        self.primary_entity_registry = bundle.entity_registry
        self.relationship_registry = bundle.relationship_registry
        self.unresolved_registry = bundle.unresolved_registry
        self.remediation_ledger = bundle.remediation_ledger
        self.legacy_entity_registry = None
        self._entities = list(bundle.entity_registry.entities)
        self._entities_by_id = {entity.id: entity for entity in bundle.entity_registry.entities}
        self._relationships = list(bundle.relationship_registry.relationships)
        self._subsets = bundle.subsets
        self._fingerprint = bundle.fingerprint
        self._model = bundle.model

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
            scope_root=(
                str(self._scope_root) if self._scope_root else str(legacy_path.parent.parent)
            ),
            architecture_namespace=getattr(self._scope_resolver.resolve(), "name", None),
            generator="adr-architecture-repository",
            extraction_phase="architecture_repository.load_legacy",
        )
        self._entities = list(adapted_model.entities)
        self._entities_by_id = {entity.id: entity for entity in adapted_model.entities}
        self._relationships = list(adapted_model.relationships)
        self._subsets = {
            "components": [
                entity for entity in adapted_model.entities if entity.entity_type == "component"
            ],
            "capabilities": [
                entity for entity in adapted_model.entities if entity.entity_type == "capability"
            ],
            "decisions": [
                entity for entity in adapted_model.entities if entity.entity_type == "decision"
            ],
            "invariants": [
                entity for entity in adapted_model.entities if entity.entity_type == "invariant"
            ],
            "systems": [
                entity for entity in adapted_model.entities if entity.entity_type == "system"
            ],
        }
        self._fingerprint = fingerprint_payload(
            {
                "mode": "legacy",
                "legacy_entity_registry": model_payload(legacy_registry),
            }
        )
        self._model = adapted_model.model_copy(update={"fingerprint": self._fingerprint})

    def _reset_state(self) -> None:
        self._scope_root = None
        self.architecture_index = None
        self.primary_entity_registry = None
        self.relationship_registry = None
        self.unresolved_registry = None
        self.remediation_ledger = None
        self.legacy_entity_registry = None
        self._model = None
        self._entities = []
        self._entities_by_id = {}
        self._relationships = []
        self._subsets = {
            "components": [],
            "capabilities": [],
            "decisions": [],
            "invariants": [],
            "systems": [],
        }
