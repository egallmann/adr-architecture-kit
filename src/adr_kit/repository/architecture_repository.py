"""Architecture Repository Boundary over compiled discovery artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
import re
import warnings
import yaml

from ..identity import UUIDV7_PATTERN, derive_alias_ref
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
from ..models.v2_0 import (
    NormalizedArchitectureModelV2,
    NormalizedEntityRegistryV2,
    NormalizedEntityV2,
    RelationshipRecordV2,
    RelationshipRegistryV2,
    UnresolvedRegistryV2,
)
from ..parser import ADRParser
from ..scope import ProjectScopeResolver
from .registry_loader import (
    fingerprint_payload,
    load_legacy_entity_registry,
    model_payload,
)
from .registry_paths import discover_repository_paths
from ._normalized_bundle import (
    SUBSET_TYPES,
    NormalizedBundle,
    NormalizedBundleV2,
    NormalizedModelVersion,
    load_normalized_bundle_from_paths,
)
from .semantic_adapter import coerce_to_normalized_model
from ..decorators import implements, implements_adr


class ArchitectureRegistryError(Exception):
    """Deterministic repository loading failure."""


@dataclass(frozen=True)
class ContractBundleView:
    """Repository-facing typed contract bundle for consumer workflows."""

    architecture_index: ArchitectureIndex
    entity_registry: NormalizedEntityRegistry | NormalizedEntityRegistryV2
    relationship_registry: RelationshipRegistry | RelationshipRegistryV2
    unresolved_registry: UnresolvedRegistry | UnresolvedRegistryV2
    remediation_ledger: RemediationLedger | None


@dataclass(frozen=True, slots=True)
class EntityAliasRecord:
    """One alias inventory row for a UUID-identity entity."""

    uuid: str
    alias_id: str
    alias_name: str
    alias_ref: str
    entity_type: str
    uri: str


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
    primary_entity_registry: NormalizedEntityRegistry | NormalizedEntityRegistryV2 | None
    relationship_registry: RelationshipRegistry | RelationshipRegistryV2 | None
    unresolved_registry: UnresolvedRegistry | UnresolvedRegistryV2 | None
    remediation_ledger: RemediationLedger | None
    legacy_entity_registry: EntityRegistry | None
    _model: NormalizedArchitectureModel | None
    _model_v2: NormalizedArchitectureModelV2 | None
    _model_version: NormalizedModelVersion | None
    _entities: list[NormalizedEntity | NormalizedEntityV2]
    _entities_by_id: dict[str, NormalizedEntity | NormalizedEntityV2]
    _entities_by_alias_id: dict[str, list[NormalizedEntityV2]]
    _entities_by_alias_ref: dict[str, list[NormalizedEntityV2]]
    _entities_by_uri: dict[str, NormalizedEntityV2]
    _relationships: list[RelationshipRecord | RelationshipRecordV2]
    _subsets: dict[str, list[NormalizedEntity | NormalizedEntityV2]]

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
        """Return the normalized semantic boundary for a model 1.1 loaded scope."""

        self.load()
        if self._model_version == "2.0":
            raise ArchitectureRegistryError(
                "Loaded model version is 2.0; use get_model_v2() for UUID-identity models"
            )
        if self._model is None:
            raise ArchitectureRegistryError(
                "Normalized architecture model unavailable before successful load"
            )
        return self._model

    def get_model_v2(self) -> NormalizedArchitectureModelV2:
        """Return the model 2.0 UUID-identity semantic boundary."""

        self.load()
        if self._model_v2 is None:
            raise ArchitectureRegistryError(
                "Normalized architecture model 2.0 unavailable for this scope"
            )
        return self._model_v2

    @property
    def model_version(self) -> NormalizedModelVersion:
        """Return the loaded normalized model schema version."""

        self.load()
        if self._model_version is None:
            raise ArchitectureRegistryError(
                "Normalized model version unavailable before successful load"
            )
        return self._model_version

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

    def get_entities(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        self.load()
        if self._model_version == "2.0":
            return list(self.get_model_v2().entities)
        return list(self.get_model().entities)

    def query_entities(
        self,
        *,
        entity_type: str | None = None,
        adr: str | None = None,
        domain: str | None = None,
        status: str | None = None,
    ) -> list[NormalizedEntity | NormalizedEntityV2]:
        """Return deterministically filtered semantic entities."""

        if self.model_version == "2.0":
            entities: list[NormalizedEntity | NormalizedEntityV2] = sorted(
                self.get_model_v2().entities, key=lambda entity: entity.id
            )
            if entity_type:
                entities = [entity for entity in entities if entity.entity_type == entity_type]
            if adr:
                entities = [
                    entity
                    for entity in entities
                    if isinstance(entity, NormalizedEntityV2)
                    and (entity.alias_id == adr or adr in self.get_entity_adr_refs(entity.id))
                ]
            if domain:
                entities = [
                    entity
                    for entity in entities
                    if isinstance(entity, NormalizedEntityV2)
                    and domain in list(entity.metadata.get("domains", []) or [])
                ]
            if status:
                entities = [entity for entity in entities if entity.lifecycle_stage == status]
            return entities

        model = self.get_model()
        legacy_entities = sorted(model.entities, key=lambda entity: entity.id)
        if entity_type:
            legacy_entities = [
                entity for entity in legacy_entities if entity.entity_type == entity_type
            ]
        if adr:
            legacy_entities = [
                entity
                for entity in legacy_entities
                if adr in model.canonical_adr_refs_for_entity(entity.id)
            ]
        if domain:
            legacy_entities = [
                entity for entity in legacy_entities if domain in model.entity_domains(entity.id)
            ]
        if status:
            legacy_entities = [
                entity for entity in legacy_entities if model.entity_status(entity.id) == status
            ]
        return list(legacy_entities)

    def get_components(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="component")

    def get_capabilities(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="capability")

    def get_decisions(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="decision")

    def get_invariants(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="invariant")

    def get_systems(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="system")

    def get_boundaries(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="boundary")

    def get_contracts(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="contract")

    def get_interfaces(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="interface")

    def get_implementation_decisions(self) -> list[NormalizedEntity | NormalizedEntityV2]:
        return self.query_entities(entity_type="implementation_decision")

    def get_relationships(self) -> list[RelationshipRecord | RelationshipRecordV2]:
        self.load()
        if self._model_version == "2.0":
            return list(self.get_model_v2().relationships)
        return list(self.get_model().relationships)

    def get_relationships_for_entity(
        self,
        entity_id: str,
        *,
        relationship_type: str | None = None,
        direction: Literal["any", "incoming", "outgoing"] = "any",
    ) -> list[RelationshipRecord | RelationshipRecordV2]:
        if self.model_version == "2.0":
            return list(
                self.get_model_v2().relationships_for_entity(
                    entity_id,
                    relationship_type=relationship_type,
                    direction=direction,
                )
            )
        return list(
            self.get_model().relationships_for_entity(
                entity_id,
                relationship_type=relationship_type,
                direction=direction,
            )
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
        if self.model_version == "2.0":
            return [
                item
                for item in self.get_model_v2().unresolved
                if item.source_entity_id == entity_id or item.related_entity_id == entity_id
            ]
        return self.get_model().unresolved_for_entity(entity_id)

    @implements_adr("ADR-L-0013")
    def get_unresolved_by_role(
        self,
        entity_id: str,
        *,
        role: Literal["source", "related", "any"] = "source",
    ) -> list[UnresolvedRecord]:
        if self.model_version == "2.0":
            unresolved = self.get_model_v2().unresolved
            if role == "source":
                return [item for item in unresolved if item.source_entity_id == entity_id]
            if role == "related":
                return [item for item in unresolved if item.related_entity_id == entity_id]
            return [
                item
                for item in unresolved
                if item.source_entity_id == entity_id or item.related_entity_id == entity_id
            ]
        return self.get_model().unresolved_for_entity(entity_id, role=role)

    def get_adr_status(self, adr_id: str) -> str | None:
        if self.model_version == "2.0":
            entity = self.find_entity_by_alias_id(adr_id)
            if entity is None:
                entity = self.find_entity_by_uuid(adr_id)
            if entity is None:
                return None
            return str(entity.metadata.get("status") or entity.lifecycle_stage)
        return self.get_model().adr_status(adr_id)

    def get_entity_provenance(self, entity_id: str) -> DiscoveryProvenance | None:
        entity = self.find_entity(entity_id)
        if entity is None:
            return None
        return entity.provenance

    @implements_adr("ADR-L-0013")
    def get_entity_canonical_source_ref(self, entity_id: str) -> str | None:
        entity = self._require_entity(entity_id)
        return entity.canonical_source.source_ref

    @implements_adr("ADR-L-0013")
    def get_entity_source_refs(self, entity_id: str) -> list[SourceRef]:
        entity = self._require_entity(entity_id)
        return list(entity.source_refs)

    def get_entity_adr_refs(self, entity_id: str) -> list[str]:
        if self.model_version == "2.0":
            entity = self._require_entity(entity_id)
            if isinstance(entity, NormalizedEntityV2):
                refs = {
                    ref
                    for ref in (
                        entity.alias_id,
                        entity.canonical_source.source_ref.split("#", 1)[0],
                    )
                    if ref.startswith("ADR-")
                }
                return sorted(refs)
            return []
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
        if not isinstance(
            self.relationship_registry, (RelationshipRegistry, RelationshipRegistryV2)
        ):
            raise ArchitectureRegistryError("Relationship registry type is unsupported")
        if not isinstance(self.unresolved_registry, (UnresolvedRegistry, UnresolvedRegistryV2)):
            raise ArchitectureRegistryError("Unresolved registry type is unsupported")
        return ContractBundleView(
            architecture_index=self.architecture_index,
            entity_registry=self.primary_entity_registry,
            relationship_registry=self.relationship_registry,
            unresolved_registry=self.unresolved_registry,
            remediation_ledger=self.remediation_ledger,
        )

    def get_corpus_summary(self) -> CorpusSummary:
        """Return deterministic corpus orientation data for the current scope."""
        if self.model_version == "2.0":
            model_v2 = self.get_model_v2()
            entity_counts: dict[str, int] = {}
            adr_counts_by_type: dict[str, int] = {}
            adr_counts_by_status: dict[str, int] = {}
            for entity_v2 in model_v2.entities:
                entity_counts[entity_v2.entity_type] = (
                    entity_counts.get(entity_v2.entity_type, 0) + 1
                )
                if entity_v2.entity_type != "adr":
                    continue
                adr_type = self._adr_type_for_id(entity_v2.alias_id)
                adr_counts_by_type[adr_type] = adr_counts_by_type.get(adr_type, 0) + 1
                adr_status = str(entity_v2.metadata.get("status") or entity_v2.lifecycle_stage)
                adr_counts_by_status[adr_status] = adr_counts_by_status.get(adr_status, 0) + 1
            return CorpusSummary(
                scope_root=model_v2.scope_root,
                architecture_namespace=model_v2.architecture_namespace,
                fingerprint=model_v2.fingerprint,
                mode=model_v2.mode,
                entity_counts=dict(sorted(entity_counts.items())),
                adr_counts_by_type=dict(sorted(adr_counts_by_type.items())),
                adr_counts_by_status=dict(sorted(adr_counts_by_status.items())),
                relationship_count=len(model_v2.relationships),
                unresolved_count=len(model_v2.unresolved),
                source_coverage=model_v2.source_coverage,
                validation_summary=model_v2.validation_summary,
            )

        model = self.get_model()
        legacy_entity_counts: dict[str, int] = {}
        legacy_adr_counts_by_type: dict[str, int] = {}
        legacy_adr_counts_by_status: dict[str, int] = {}

        for entity in model.entities:
            legacy_entity_counts[entity.entity_type] = (
                legacy_entity_counts.get(entity.entity_type, 0) + 1
            )
            if entity.entity_type != "adr":
                continue
            adr_type = self._adr_type_for_id(entity.id)
            legacy_adr_counts_by_type[adr_type] = legacy_adr_counts_by_type.get(adr_type, 0) + 1
            adr_status = model.adr_status(entity.id) or "unknown"
            legacy_adr_counts_by_status[adr_status] = (
                legacy_adr_counts_by_status.get(adr_status, 0) + 1
            )

        return CorpusSummary(
            scope_root=model.scope_root,
            architecture_namespace=model.architecture_namespace,
            fingerprint=model.fingerprint,
            mode=model.mode,
            entity_counts=dict(sorted(legacy_entity_counts.items())),
            adr_counts_by_type=dict(sorted(legacy_adr_counts_by_type.items())),
            adr_counts_by_status=dict(sorted(legacy_adr_counts_by_status.items())),
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

    @implements("019fee89-e617-7fe1-8d2c-cc2745c31674")
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

                effective_alias = self._effective_allocation_alias(data, pattern)
                if effective_alias is None:
                    continue

                existing_path = seen_ids.get(effective_alias)
                if existing_path is not None:
                    raise ArchitectureRegistryError(
                        f"Duplicate ADR ID in {target_dir}: {effective_alias} declared in both {existing_path.name} and {path.name}"
                    )
                seen_ids[effective_alias] = path

                match = pattern.match(effective_alias)
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

    @staticmethod
    def _effective_allocation_alias(data: dict[str, Any], pattern: re.Pattern[str]) -> str | None:
        """Return the human ADR alias used for next-id occupancy, if any.

        v1.3 documents sequence from ``alias_id``. Legacy documents sequence from
        a patterned ``id``. A UUID-valued ``id`` never participates.
        """

        alias_id = data.get("alias_id")
        if isinstance(alias_id, str) and alias_id.strip():
            candidate = alias_id.strip()
            return candidate if pattern.match(candidate) else None

        declared_id = data.get("id")
        if isinstance(declared_id, str) and pattern.match(declared_id):
            return declared_id
        return None

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

    def find_entity(self, entity_id: str) -> NormalizedEntity | NormalizedEntityV2 | None:
        """Locate an entity by canonical UUID or unique alias compatibility shim."""

        self.load()
        if self._model_version == "2.0":
            by_uuid = self.find_entity_by_uuid(entity_id)
            if by_uuid is not None:
                return by_uuid
            matches = list(self._entities_by_alias_id.get(entity_id, []))
            if len(matches) == 1:
                warnings.warn(
                    "find_entity(alias_id) is deprecated through 0.4.x; "
                    "use find_entity_by_alias_id() or resolve by UUID",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return matches[0]
            if len(matches) > 1:
                raise ArchitectureRegistryError(
                    f"Ambiguous alias_id {entity_id!r}: matches {len(matches)} entities"
                )
            return None
        return self.get_model().find_entity(entity_id)

    @implements_adr("ADR-L-0019", "ADR-L-0016")
    def find_entity_by_uuid(self, uuid: str) -> NormalizedEntityV2 | None:
        """Find a model 2.0 entity by canonical UUIDv7."""

        self.load()
        self._require_model_v2()
        if not isinstance(uuid, str) or not UUIDV7_PATTERN.match(uuid):
            return None
        entity = self._entities_by_id.get(uuid)
        return entity if isinstance(entity, NormalizedEntityV2) else None

    @implements_adr("ADR-L-0019", "ADR-L-0016")
    def find_entity_by_alias_id(self, alias_id: str) -> NormalizedEntityV2 | None:
        """Find a model 2.0 entity by unique alias_id; fail on ambiguity."""

        self.load()
        self._require_model_v2()
        matches = list(self._entities_by_alias_id.get(alias_id, []))
        if not matches:
            return None
        if len(matches) > 1:
            raise ArchitectureRegistryError(
                f"Ambiguous alias_id {alias_id!r}: matches {len(matches)} entities"
            )
        return matches[0]

    @implements_adr("ADR-L-0019", "ADR-L-0016")
    def find_entity_by_alias_ref(self, alias_ref: str) -> NormalizedEntityV2 | None:
        """Find a model 2.0 entity by unique alias_ref; fail on ambiguity."""

        self.load()
        self._require_model_v2()
        matches = list(self._entities_by_alias_ref.get(alias_ref, []))
        if not matches:
            return None
        if len(matches) > 1:
            raise ArchitectureRegistryError(
                f"Ambiguous alias_ref {alias_ref!r}: matches {len(matches)} entities"
            )
        return matches[0]

    @implements_adr("ADR-L-0019", "ADR-L-0016")
    def resolve_uri(self, uri: str) -> NormalizedEntityV2:
        """Resolve an adr:// URI within this provider repository."""

        self.load()
        self._require_model_v2()
        entity = self._entities_by_uri.get(uri)
        if entity is None:
            raise ArchitectureRegistryError(f"Entity URI not found: {uri}")
        namespace = self.get_model_v2().architecture_namespace
        if namespace and not uri.startswith(f"adr://{namespace}/entities/"):
            raise ArchitectureRegistryError(
                f"URI namespace does not match provider architecture_namespace {namespace!r}"
            )
        return entity

    @implements_adr("ADR-L-0019", "ADR-L-0016")
    def list_aliases(self) -> list[EntityAliasRecord]:
        """Return deterministic alias inventory for model 2.0 entities."""

        self.load()
        self._require_model_v2()
        records = [
            EntityAliasRecord(
                uuid=entity.id,
                alias_id=entity.alias_id,
                alias_name=entity.alias_name,
                alias_ref=entity.alias_ref or derive_alias_ref(entity.alias_id, entity.alias_name),
                entity_type=entity.entity_type,
                uri=entity.uri,
            )
            for entity in self.get_model_v2().entities
        ]
        return sorted(records, key=lambda item: (item.alias_id, item.uuid))

    @implements_adr("ADR-L-0019", "ADR-L-0016")
    def resolve_entity_reference(self, reference: str) -> str:
        """Resolve a convenience reference to the canonical UUID."""

        self.load()
        self._require_model_v2()
        if UUIDV7_PATTERN.match(reference):
            entity = self.find_entity_by_uuid(reference)
            if entity is None:
                raise ArchitectureRegistryError(f"Entity not found: {reference}")
            return entity.id
        if reference.startswith("adr://"):
            return self.resolve_uri(reference).id
        if ":" in reference:
            entity = self.find_entity_by_alias_ref(reference)
            if entity is not None:
                return entity.id
        entity = self.find_entity_by_alias_id(reference)
        if entity is not None:
            return entity.id
        raise ArchitectureRegistryError(f"Entity reference not found: {reference}")

    def _require_model_v2(self) -> None:
        if self._model_version != "2.0" or self._model_v2 is None:
            raise ArchitectureRegistryError(
                "UUID/alias/URI identity APIs require a loaded model 2.0 bundle"
            )

    def _require_entity(self, entity_id: str) -> NormalizedEntity | NormalizedEntityV2:
        entity = self.find_entity(entity_id)
        if entity is None:
            raise ArchitectureRegistryError(f"Entity not found: {entity_id}")
        return entity

    def _get_subset(self, name: str) -> list[NormalizedEntity | NormalizedEntityV2]:
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
        self._fingerprint = bundle.fingerprint
        self._model_version = bundle.model_version
        if isinstance(bundle, NormalizedBundleV2):
            self._model = None
            self._model_v2 = bundle.model
            self._entities = list(bundle.entity_registry.entities)
            self._entities_by_id = {entity.id: entity for entity in bundle.entity_registry.entities}
            self._relationships = list(bundle.relationship_registry.relationships)
            self._subsets = {name: list(values) for name, values in bundle.subsets.items()}
            self._index_v2_aliases(bundle.entity_registry.entities)
        elif isinstance(bundle, NormalizedBundle):
            self._model = bundle.model
            self._model_v2 = None
            self._entities = list(bundle.entity_registry.entities)
            self._entities_by_id = {entity.id: entity for entity in bundle.entity_registry.entities}
            self._relationships = list(bundle.relationship_registry.relationships)
            self._subsets = {name: list(values) for name, values in bundle.subsets.items()}
            self._entities_by_alias_id = {}
            self._entities_by_alias_ref = {}
            self._entities_by_uri = {}
        else:
            raise ArchitectureRegistryError("Unsupported normalized bundle type")

    def _index_v2_aliases(self, entities: list[NormalizedEntityV2]) -> None:
        by_alias_id: dict[str, list[NormalizedEntityV2]] = {}
        by_alias_ref: dict[str, list[NormalizedEntityV2]] = {}
        by_uri: dict[str, NormalizedEntityV2] = {}
        for entity in entities:
            by_alias_id.setdefault(entity.alias_id, []).append(entity)
            alias_ref = entity.alias_ref or derive_alias_ref(entity.alias_id, entity.alias_name)
            by_alias_ref.setdefault(alias_ref, []).append(entity)
            by_uri[entity.uri] = entity
        self._entities_by_alias_id = by_alias_id
        self._entities_by_alias_ref = by_alias_ref
        self._entities_by_uri = by_uri

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
        self._model_v2 = None
        self._model_version = "1.1"
        self._entities_by_alias_id = {}
        self._entities_by_alias_ref = {}
        self._entities_by_uri = {}

    def _reset_state(self) -> None:
        self._scope_root = None
        self.architecture_index = None
        self.primary_entity_registry = None
        self.relationship_registry = None
        self.unresolved_registry = None
        self.remediation_ledger = None
        self.legacy_entity_registry = None
        self._model = None
        self._model_v2 = None
        self._model_version = None
        self._entities = []
        self._entities_by_id = {}
        self._entities_by_alias_id = {}
        self._entities_by_alias_ref = {}
        self._entities_by_uri = {}
        self._relationships = []
        self._subsets = {
            "components": [],
            "capabilities": [],
            "decisions": [],
            "invariants": [],
            "systems": [],
        }
