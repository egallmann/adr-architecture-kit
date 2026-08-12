"""Entity Registry Generator - creates entity registry from canonical artifacts."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ..compiler.frontend.adr_access import (
    field_get,
    field_list,
    is_physical_component_adr,
    is_physical_system_adr,
    presentation_id,
)
from ..decorators import implements_adr
from ..models import (
    Entity,
    EntityOwnership,
    EntityRegistry,
    EntityRelationships,
    EntityType,
    LifecycleStage,
    LogicalADR,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
    SourceArtifactType,
    StandaloneInvariant,
)
from ..pathing import manifest_relative_path
from ..parser import ADRParser
from ..scope import ProjectScope, ProjectScopeResolver


@implements_adr("ADR-L-0009", "ADR-L-0013", "ADR-PC-0001")
class EntityRegistryGenerator:
    """Generate deterministic entity registry from canonical architecture artifacts."""

    def __init__(self, parser: ADRParser = None, scope_resolver: ProjectScopeResolver = None):
        self.parser = parser or ADRParser()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()

    def _discover_artifact_files(
        self, adr_dir: Path
    ) -> tuple[list[Path], list[Path], list[Path]]:
        """Discover logical and physical ADRs; refuse retired standalone invariants dir."""
        from ..compiler.frontend.support import discover_source_files

        return discover_source_files(adr_dir)

    def _source_path(self, scope_root: Path, file_path: Path) -> str:
        """Return stable scope-relative source path."""
        return manifest_relative_path(scope_root, file_path).replace("\\", "/")

    def _map_status_to_lifecycle(self, status) -> LifecycleStage:
        """Map ADR status to entity lifecycle stage."""
        status_str = status.value if hasattr(status, "value") else str(status)
        mapping = {
            "proposed": LifecycleStage.PROPOSED,
            "accepted": LifecycleStage.ACTIVE,
            "deprecated": LifecycleStage.DEPRECATED,
            "superseded": LifecycleStage.SUPERSEDED,
        }
        return mapping.get(status_str, LifecycleStage.ACTIVE)

    def _ownership(self, adr: Any) -> Optional[EntityOwnership]:
        """Derive ownership metadata from source ADR."""
        ownership = field_get(adr, "ownership")
        if ownership is None:
            return None
        return EntityOwnership(
            architecture_authority=field_get(ownership, "architecture_authority"),
            implementation_owners=list(field_list(ownership, "implementation_owners")),
        )

    def _entity_name(self, value: str, limit: int = 120) -> str:
        """Normalize human-readable names while keeping deterministic truncation."""
        normalized = " ".join(value.split())
        return normalized[:limit]

    def _add_entity(self, entities: Dict[str, Entity], entity: Entity) -> None:
        """Add entity and fail on duplicates."""
        existing = entities.get(entity.entity_id)
        if existing is not None:
            raise ValueError(
                f"Duplicate entity ID {entity.entity_id} in {entity.source_path} "
                f"(already defined in {existing.source_path})"
            )
        entities[entity.entity_id] = entity

    def _append_realized_by(self, entities: Dict[str, Entity], entity_id: str, ref: str) -> None:
        """Append deterministic realized_by reference when target exists."""
        entity = entities.get(entity_id)
        if entity is None:
            return
        if ref not in entity.realized_by:
            entity.realized_by.append(ref)
            entity.realized_by.sort()

    def _introduced_ids(self, adr: Any) -> set[str]:
        """Return explicitly introduced entity IDs for an ADR."""
        return set(getattr(adr, "introduces_entities", []) or [])

    def _index_presentation_ids(
        self,
        logical_adrs: List[Tuple[LogicalADR, Path]],
        physical_adrs: List[Tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]],
        standalone_invariants: List[Tuple[StandaloneInvariant, Path]],
    ) -> dict[str, str]:
        """Map canonical UUID ids to governed alias presentation ids."""
        uuid_to_alias: dict[str, str] = {}

        def index(obj) -> None:
            obj_id = field_get(obj, "id")
            alias = field_get(obj, "alias_id")
            if isinstance(obj_id, str) and isinstance(alias, str) and alias:
                uuid_to_alias[obj_id] = alias

        for adr, _ in logical_adrs + physical_adrs:
            index(adr)
            for section in (
                "capabilities",
                "architectural_boundaries",
                "interaction_contracts",
                "constraints",
                "invariants",
                "nfrs",
                "decisions",
                "gaps",
                "component_specifications",
                "integration_points",
                "implementation_decisions",
            ):
                for item in field_list(adr, section):
                    index(item)
                    for iface in field_list(item, "interfaces"):
                        index(iface)
        for inv, _ in standalone_invariants:
            index(inv)
        return uuid_to_alias

    def _ref(self, uuid_to_alias: dict[str, str], value: str) -> str:
        """Resolve a reference to legacy presentation id when possible."""
        return uuid_to_alias.get(value, value)

    def _refs(self, uuid_to_alias: dict[str, str], values: List[str] | None) -> List[str]:
        return [self._ref(uuid_to_alias, value) for value in (values or [])]

    def _related_adrs(
        self,
        adr: Any,
        uuid_to_alias: dict[str, str],
        extra: Optional[List[str]] = None,
    ) -> List[str]:
        """Build sorted related ADR presentation references for discovery."""
        related = set(getattr(adr, "related_adrs", []) or [])
        related.update(getattr(adr, "supersedes", []) or [])
        superseded_by = getattr(adr, "superseded_by", None)
        if superseded_by:
            related.add(superseded_by)
        if extra:
            related.update(extra)
        return sorted(self._ref(uuid_to_alias, item) for item in related)

    def generate_from_directory(self, adr_dir: Path, scope: Optional[ProjectScope] = None) -> EntityRegistry:
        """Generate entity registry from ADR directory."""
        adr_dir = Path(adr_dir).resolve()
        if not adr_dir.exists():
            raise ValueError(f"ADR directory not found: {adr_dir}")

        if scope is None:
            scope = self.scope_resolver.resolve(adr_dir.parent)

        logical_files, physical_files, invariant_files = self._discover_artifact_files(adr_dir)

        logical_adrs: List[Tuple[LogicalADR, Path]] = []
        physical_adrs: List[Tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]] = []
        standalone_invariants: List[Tuple[StandaloneInvariant, Path]] = []

        for file_path in logical_files:
            logical_adrs.append((self.parser.parse_logical_adr(file_path), file_path.resolve()))

        for file_path in physical_files:
            physical_adrs.append((self.parser.parse_adr(file_path), file_path.resolve()))

        for file_path in invariant_files:
            standalone_invariants.append((self.parser.parse_invariant(file_path), file_path.resolve()))

        uuid_to_alias = self._index_presentation_ids(logical_adrs, physical_adrs, standalone_invariants)

        adr_lifecycle_by_id = {
            adr.id: self._map_status_to_lifecycle(adr.status)
            for adr, _ in logical_adrs + physical_adrs
        }
        # Also index by presentation id for defined_in lookups that may use either form.
        for adr, _ in logical_adrs + physical_adrs:
            alias = field_get(adr, "alias_id")
            if isinstance(alias, str) and alias:
                adr_lifecycle_by_id[alias] = self._map_status_to_lifecycle(adr.status)

        entities: Dict[str, Entity] = {}

        for adr, file_path in logical_adrs:
            lifecycle = self._map_status_to_lifecycle(adr.status)
            source_path = self._source_path(scope.root, file_path)
            ownership = self._ownership(adr)
            related_adrs = self._related_adrs(adr, uuid_to_alias)
            introduced_ids = self._introduced_ids(adr)
            introduced_by = presentation_id(adr)

            for cap in adr.capabilities:
                if cap.id not in introduced_ids:
                    continue
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=presentation_id(cap),
                        entity_type=EntityType.CAPABILITY,
                        name=cap.name,
                        introduced_by=introduced_by,
                        lifecycle_stage=lifecycle,
                        source_path=source_path,
                        source_artifact_type=SourceArtifactType.LOGICAL_ADR,
                        domains=list(adr.domains),
                        related_adrs=related_adrs,
                        ownership=ownership,
                    ),
                )

            for inv in adr.invariants:
                if inv.id not in introduced_ids:
                    continue
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=presentation_id(inv),
                        entity_type=EntityType.INVARIANT,
                        name=self._entity_name(inv.statement),
                        introduced_by=introduced_by,
                        lifecycle_stage=lifecycle,
                        source_path=source_path,
                        source_artifact_type=SourceArtifactType.LOGICAL_ADR,
                        domains=list(adr.domains),
                        related_adrs=related_adrs,
                        ownership=ownership,
                    ),
                )

        for adr, file_path in physical_adrs:
            lifecycle = self._map_status_to_lifecycle(adr.status)
            source_path = self._source_path(scope.root, file_path)
            ownership = self._ownership(adr)
            extra_related = list(getattr(adr, "implements_logical", []) or [])
            if is_physical_component_adr(adr):
                extra_related.extend(list(getattr(adr, "implements_system", []) or []))
            related_adrs = self._related_adrs(adr, uuid_to_alias, extra=extra_related)
            introduced_ids = self._introduced_ids(adr)
            introduced_by = presentation_id(adr)

            source_type = SourceArtifactType.PHYSICAL_ADR
            if is_physical_system_adr(adr):
                source_type = SourceArtifactType.PHYSICAL_SYSTEM_ADR
            elif is_physical_component_adr(adr):
                source_type = SourceArtifactType.PHYSICAL_COMPONENT_ADR

            for comp in field_list(adr, "component_specifications"):
                comp_canonical_id = field_get(comp, "id")
                if comp_canonical_id not in introduced_ids:
                    continue
                comp_id = presentation_id(comp)
                comp_name = field_get(comp, "name") or comp_id
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=comp_id,
                        entity_type=EntityType.COMPONENT,
                        name=comp_name,
                        introduced_by=introduced_by,
                        lifecycle_stage=lifecycle,
                        source_path=source_path,
                        source_artifact_type=source_type,
                        domains=list(adr.domains),
                        related_adrs=related_adrs,
                        realized_by=[introduced_by],
                        ownership=ownership,
                        relationships=EntityRelationships(
                            depends_on=self._refs(
                                uuid_to_alias, field_list(comp, "dependencies")
                            ),
                            implements=self._refs(
                                uuid_to_alias,
                                field_list(comp, "implements_capabilities"),
                            ),
                            consumes=self._refs(
                                uuid_to_alias,
                                field_list(comp, "upstream_services"),
                            ),
                            realizes=self._refs(
                                uuid_to_alias,
                                field_list(comp, "realizes_entities"),
                            ),
                        ),
                    ),
                )

                for iface in field_list(comp, "interfaces"):
                    iface_canonical_id = field_get(iface, "id")
                    if iface_canonical_id not in introduced_ids:
                        continue
                    iface_name = (
                        field_get(iface, "name")
                        or field_get(iface, "type")
                        or "interface"
                    )
                    self._add_entity(
                        entities,
                        Entity(
                            entity_id=presentation_id(iface),
                            entity_type=EntityType.INTERFACE,
                            name=self._entity_name(f"{comp_name} {iface_name}"),
                            introduced_by=introduced_by,
                            lifecycle_stage=lifecycle,
                            source_path=source_path,
                            source_artifact_type=source_type,
                            domains=list(adr.domains),
                            related_adrs=related_adrs,
                            realized_by=[comp_id, introduced_by],
                            ownership=ownership,
                        ),
                    )

            for integ in field_list(adr, "integration_points"):
                integ_canonical_id = field_get(integ, "id")
                if integ_canonical_id not in introduced_ids:
                    continue
                related = set(related_adrs)
                contract_adr = field_get(integ, "contract_adr")
                if contract_adr:
                    related.add(self._ref(uuid_to_alias, contract_adr))
                systems = field_list(integ, "systems")
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=presentation_id(integ),
                        entity_type=EntityType.INTEGRATION,
                        name=self._entity_name(" -> ".join(str(item) for item in systems)),
                        introduced_by=introduced_by,
                        lifecycle_stage=lifecycle,
                        source_path=source_path,
                        source_artifact_type=source_type,
                        domains=list(adr.domains),
                        related_adrs=sorted(related),
                        realized_by=[introduced_by],
                        ownership=ownership,
                    ),
                )

            for impl_dec in field_list(adr, "implementation_decisions"):
                impl_canonical_id = field_get(impl_dec, "id")
                if impl_canonical_id not in introduced_ids:
                    continue
                realized = {introduced_by}
                realized.update(
                    self._refs(
                        uuid_to_alias,
                        field_list(impl_dec, "implements_invariants"),
                    )
                )
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=presentation_id(impl_dec),
                        entity_type=EntityType.IMPLEMENTATION_DECISION,
                        name=field_get(impl_dec, "summary") or presentation_id(impl_dec),
                        introduced_by=introduced_by,
                        lifecycle_stage=lifecycle,
                        source_path=source_path,
                        source_artifact_type=source_type,
                        domains=list(adr.domains),
                        related_adrs=related_adrs,
                        realized_by=sorted(realized),
                        ownership=ownership,
                    ),
                )

        for inv, file_path in standalone_invariants:
            defined_in = field_get(inv, "defined_in")
            if not defined_in:
                raise ValueError(f"Standalone invariant {presentation_id(inv)} is missing defined_in")
            source_path = self._source_path(scope.root, file_path)
            defined_in_ref = self._ref(uuid_to_alias, str(defined_in))
            lifecycle = adr_lifecycle_by_id.get(str(defined_in), LifecycleStage.ACTIVE)
            if str(defined_in) in uuid_to_alias:
                lifecycle = adr_lifecycle_by_id.get(uuid_to_alias[str(defined_in)], lifecycle)
            self._add_entity(
                entities,
                Entity(
                    entity_id=presentation_id(inv),
                    entity_type=EntityType.INVARIANT,
                    name=self._entity_name(str(field_get(inv, "statement") or "")),
                    introduced_by=defined_in_ref,
                    lifecycle_stage=lifecycle,
                    source_path=source_path,
                    source_artifact_type=SourceArtifactType.STANDALONE_INVARIANT,
                    domains=[],
                    related_adrs=[defined_in_ref],
                    realized_by=sorted(
                        self._refs(uuid_to_alias, field_list(inv, "enforced_by"))
                    ),
                    relationships=EntityRelationships(
                        implements=self._refs(
                            uuid_to_alias, field_list(inv, "related_constraints")
                        ),
                    ),
                ),
            )

        for adr, _ in physical_adrs:
            adr_ref = presentation_id(adr)
            for entity_id in field_list(adr, "realizes_entities"):
                self._append_realized_by(entities, self._ref(uuid_to_alias, entity_id), adr_ref)

            for comp in field_list(adr, "component_specifications"):
                comp_ref = presentation_id(comp)
                for entity_id in field_list(comp, "implements_capabilities"):
                    self._append_realized_by(
                        entities, self._ref(uuid_to_alias, entity_id), comp_ref
                    )
                for entity_id in field_list(comp, "realizes_entities"):
                    self._append_realized_by(
                        entities, self._ref(uuid_to_alias, entity_id), comp_ref
                    )

        return EntityRegistry(
            schema_version="1.1",
            type="entity_registry",
            entities=sorted(entities.values(), key=lambda entity: entity.entity_id),
        )

    def generate_from_scope(self, scope: Optional[ProjectScope] = None) -> EntityRegistry:
        """Generate entity registry for a resolved project scope."""
        if scope is None:
            scope = self.scope_resolver.resolve()
        return self.generate_from_directory(scope.adr_dir, scope)

    def generate_recursive(self, scope: Optional[ProjectScope] = None) -> Dict[str, EntityRegistry]:
        """Generate entity registries for all scopes recursively."""
        if scope is None:
            scope = self.scope_resolver.resolve()

        registries: Dict[str, EntityRegistry] = {}
        for current_scope in self.scope_resolver.resolve_recursive(scope.root):
            if current_scope.adr_dir.exists():
                registries[current_scope.name or str(current_scope.root)] = self.generate_from_directory(
                    current_scope.adr_dir,
                    current_scope,
                )
        return registries

    def render_registry_yaml(self, registry: EntityRegistry) -> str:
        """Render deterministic registry YAML."""
        return yaml.safe_dump(
            registry.model_dump(mode="json", exclude_none=True),
            sort_keys=False,
            allow_unicode=True,
        )

    def save_registry(self, registry: EntityRegistry, output_path: Path):
        """Save registry to YAML file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="\n") as file:
            file.write(self.render_registry_yaml(registry))
