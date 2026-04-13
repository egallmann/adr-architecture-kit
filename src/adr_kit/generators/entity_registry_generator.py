"""Entity Registry Generator - creates entity registry from canonical artifacts."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

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
        """Discover logical ADRs, physical ADRs, and standalone invariants."""
        logical_files = (
            sorted((adr_dir / "logical").glob("*.yaml"))
            if (adr_dir / "logical").exists()
            else []
        )

        physical_files: list[Path] = []
        for dirname in ("physical", "physical-system", "physical-component"):
            candidate_dir = adr_dir / dirname
            if candidate_dir.exists():
                physical_files.extend(sorted(candidate_dir.glob("*.yaml")))

        invariant_files = (
            sorted((adr_dir / "invariants").glob("*.yaml"))
            if (adr_dir / "invariants").exists()
            else []
        )

        deduped_physical = list(dict.fromkeys(path.resolve() for path in physical_files))
        return logical_files, [Path(path) for path in deduped_physical], invariant_files

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

    def _ownership(self, adr) -> Optional[EntityOwnership]:
        """Derive ownership metadata from source ADR."""
        if not getattr(adr, "ownership", None):
            return None
        return EntityOwnership(
            architecture_authority=adr.ownership.architecture_authority,
            implementation_owners=list(adr.ownership.implementation_owners),
        )

    def _related_adrs(self, adr, extra: Optional[List[str]] = None) -> List[str]:
        """Build sorted related ADR references for discovery."""
        related = set(getattr(adr, "related_adrs", []) or [])
        related.update(getattr(adr, "supersedes", []) or [])
        superseded_by = getattr(adr, "superseded_by", None)
        if superseded_by:
            related.add(superseded_by)
        if extra:
            related.update(extra)
        return sorted(related)

    def _entity_name(self, value: str, limit: int = 120) -> str:
        """Normalize human-readable names while keeping deterministic truncation."""
        normalized = " ".join(value.split())
        return normalized[:limit]

    def _add_entity(self, entities: Dict[str, Entity], entity: Entity):
        """Add entity and fail on duplicates."""
        existing = entities.get(entity.entity_id)
        if existing is not None:
            raise ValueError(
                f"Duplicate entity ID {entity.entity_id} in {entity.source_path} "
                f"(already defined in {existing.source_path})"
            )
        entities[entity.entity_id] = entity

    def _append_realized_by(self, entities: Dict[str, Entity], entity_id: str, ref: str):
        """Append deterministic realized_by reference when target exists."""
        entity = entities.get(entity_id)
        if entity is None:
            return
        if ref not in entity.realized_by:
            entity.realized_by.append(ref)
            entity.realized_by.sort()

    def _introduced_ids(self, adr) -> set[str]:
        """Return explicitly introduced entity IDs for an ADR."""
        return set(getattr(adr, "introduces_entities", []) or [])

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

        adr_lifecycle_by_id = {
            adr.id: self._map_status_to_lifecycle(adr.status)
            for adr, _ in logical_adrs + physical_adrs
        }

        entities: Dict[str, Entity] = {}

        for adr, file_path in logical_adrs:
            lifecycle = self._map_status_to_lifecycle(adr.status)
            source_path = self._source_path(scope.root, file_path)
            ownership = self._ownership(adr)
            related_adrs = self._related_adrs(adr)

            introduced_ids = self._introduced_ids(adr)

            for cap in adr.capabilities:
                if cap.id not in introduced_ids:
                    continue
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=cap.id,
                        entity_type=EntityType.CAPABILITY,
                        name=cap.name,
                        introduced_by=adr.id,
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
                        entity_id=inv.id,
                        entity_type=EntityType.INVARIANT,
                        name=self._entity_name(inv.statement),
                        introduced_by=adr.id,
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
            if isinstance(adr, PhysicalComponentADR):
                extra_related.extend(list(adr.implements_system))
            related_adrs = self._related_adrs(adr, extra=extra_related)
            introduced_ids = self._introduced_ids(adr)

            source_type = SourceArtifactType.PHYSICAL_ADR
            if isinstance(adr, PhysicalSystemADR):
                source_type = SourceArtifactType.PHYSICAL_SYSTEM_ADR
            elif isinstance(adr, PhysicalComponentADR):
                source_type = SourceArtifactType.PHYSICAL_COMPONENT_ADR

            for comp in getattr(adr, "component_specifications", []):
                if comp.id not in introduced_ids:
                    continue
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=comp.id,
                        entity_type=EntityType.COMPONENT,
                        name=comp.name,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        source_path=source_path,
                        source_artifact_type=source_type,
                        domains=list(adr.domains),
                        related_adrs=related_adrs,
                        realized_by=[adr.id],
                        ownership=ownership,
                        relationships=EntityRelationships(
                            depends_on=list(getattr(comp, "dependencies", []) or []),
                            implements=list(getattr(comp, "implements_capabilities", []) or []),
                            consumes=list(getattr(comp, "upstream_services", []) or []),
                            realizes=list(getattr(comp, "realizes_entities", []) or []),
                        ),
                    ),
                )

                for iface in getattr(comp, "interfaces", []):
                    if iface.id not in introduced_ids:
                        continue
                    iface_name = getattr(iface, "name", None) or getattr(iface, "type", None) or "interface"
                    self._add_entity(
                        entities,
                        Entity(
                            entity_id=iface.id,
                            entity_type=EntityType.INTERFACE,
                            name=self._entity_name(f"{comp.name} {iface_name}"),
                            introduced_by=adr.id,
                            lifecycle_stage=lifecycle,
                            source_path=source_path,
                            source_artifact_type=source_type,
                            domains=list(adr.domains),
                            related_adrs=related_adrs,
                            realized_by=[comp.id, adr.id],
                            ownership=ownership,
                        ),
                    )

            for integ in getattr(adr, "integration_points", []):
                if integ.id not in introduced_ids:
                    continue
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=integ.id,
                        entity_type=EntityType.INTEGRATION,
                        name=self._entity_name(" -> ".join(integ.systems)),
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        source_path=source_path,
                        source_artifact_type=source_type,
                        domains=list(adr.domains),
                        related_adrs=sorted(set(related_adrs + ([integ.contract_adr] if integ.contract_adr else []))),
                        realized_by=[adr.id],
                        ownership=ownership,
                    ),
                )

            for impl_dec in getattr(adr, "implementation_decisions", []):
                if impl_dec.id not in introduced_ids:
                    continue
                self._add_entity(
                    entities,
                    Entity(
                        entity_id=impl_dec.id,
                        entity_type=EntityType.IMPLEMENTATION_DECISION,
                        name=impl_dec.summary,
                        introduced_by=adr.id,
                        lifecycle_stage=lifecycle,
                        source_path=source_path,
                        source_artifact_type=source_type,
                        domains=list(adr.domains),
                        related_adrs=related_adrs,
                        realized_by=sorted(set([adr.id] + list(getattr(impl_dec, "implements_invariants", []) or []))),
                        ownership=ownership,
                    ),
                )

        for inv, file_path in standalone_invariants:
            if not inv.defined_in:
                raise ValueError(f"Standalone invariant {inv.id} is missing defined_in")
            source_path = self._source_path(scope.root, file_path)
            lifecycle = adr_lifecycle_by_id.get(inv.defined_in, LifecycleStage.ACTIVE)
            self._add_entity(
                entities,
                Entity(
                    entity_id=inv.id,
                    entity_type=EntityType.INVARIANT,
                    name=self._entity_name(inv.statement),
                    introduced_by=inv.defined_in,
                    lifecycle_stage=lifecycle,
                    source_path=source_path,
                    source_artifact_type=SourceArtifactType.STANDALONE_INVARIANT,
                    domains=[],
                    related_adrs=[inv.defined_in],
                    realized_by=sorted(inv.enforced_by),
                    relationships=EntityRelationships(
                        implements=list(inv.related_constraints),
                    ),
                ),
            )

        for adr, _ in physical_adrs:
            for entity_id in getattr(adr, "realizes_entities", []) or []:
                self._append_realized_by(entities, entity_id, adr.id)

            for comp in getattr(adr, "component_specifications", []):
                for entity_id in list(getattr(comp, "implements_capabilities", []) or []):
                    self._append_realized_by(entities, entity_id, comp.id)
                for entity_id in list(getattr(comp, "realizes_entities", []) or []):
                    self._append_realized_by(entities, entity_id, comp.id)

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
