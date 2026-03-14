"""Architecture discovery generator for normalized index artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

from ..compiler.diagnostics import DiagnosticLog
from ..compiler.frontend.parser import CachedADRParser
from ..compiler.passes import (
    FixedOrderArchitecturePassRunner,
    score_completeness,
    validate_bundle,
)
from ..models import (
    ArchitectureIndex,
    CanonicalSource,
    Completeness,
    DiscoveryProvenance,
    Entity,
    EntityRegistry,
    EntityRelationships,
    EntityType,
    LifecycleStage,
    LogicalADR,
    NormalizedEntity,
    NormalizedEntityRegistry,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
    RelationshipRecord,
    RelationshipRegistry,
    SourceArtifactType,
    SourceCoverageSummary,
    SourceRef,
    StandaloneInvariant,
    UnresolvedRecord,
    UnresolvedRegistry,
    ValidationSummary,
)
from ..parser import ADRParser
from ..scope import ProjectScope, ProjectScopeResolver


GENERATOR_ID = "adr-architecture-index"


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


class ArchitectureIndexGenerator:
    """Generate normalized architecture discovery artifacts."""

    def __init__(self, parser: ADRParser | CachedADRParser = None, scope_resolver: ProjectScopeResolver = None):
        self.parser = parser if isinstance(parser, CachedADRParser) else CachedADRParser(parser or ADRParser())
        self.diagnostics = DiagnosticLog()
        self.pass_runner = FixedOrderArchitecturePassRunner()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()

    def _discover_source_files(self, adr_dir: Path) -> tuple[list[Path], list[Path], list[Path]]:
        logical = sorted((adr_dir / "logical").glob("*.yaml")) if (adr_dir / "logical").exists() else []
        physical: list[Path] = []
        for dirname in ("physical", "physical-system", "physical-component"):
            base = adr_dir / dirname
            if base.exists():
                physical.extend(sorted(base.glob("*.yaml")))
        invariants = sorted((adr_dir / "invariants").glob("*.yaml")) if (adr_dir / "invariants").exists() else []
        deduped = list(dict.fromkeys(path.resolve() for path in physical))
        return logical, [Path(path) for path in deduped], invariants

    def _source_path(self, scope: ProjectScope, file_path: Path) -> str:
        return str(file_path.resolve().relative_to(scope.root.resolve())).replace("\\", "/")

    def _load_namespace(self, scope: ProjectScope) -> str:
        data = self.parser.parse_yaml(scope.root / "PROJECT.yaml")
        namespace = ((data.get("architecture_documentation") or {}).get("architecture_namespace"))
        if not namespace:
            raise ValueError("PROJECT.yaml is missing architecture_documentation.architecture_namespace")
        return namespace

    def _provenance(self, source_type: str, source_ref: str, phase: str, classification: str) -> DiscoveryProvenance:
        return DiscoveryProvenance(
            source_type=source_type,
            source_ref=source_ref,
            extraction_phase=phase,
            classification=classification,
            generator=GENERATOR_ID,
        )

    def _canonical(self, source_type: str, source_ref: str, artifact_path: str) -> CanonicalSource:
        return CanonicalSource(source_type=source_type, source_ref=source_ref, artifact_path=artifact_path)

    def _complete(self, missing_fields: Optional[list[str]] = None) -> Completeness:
        return score_completeness(missing_fields)

    def _summary(self, text: str, limit: int = 220) -> str:
        return " ".join((text or "").split())[:limit]

    def _filtered(self, registry: NormalizedEntityRegistry, entity_type: str) -> NormalizedEntityRegistry:
        return NormalizedEntityRegistry(entities=[e for e in registry.entities if e.entity_type == entity_type])

    def _system_entity_id(self, adr_id: str) -> str:
        return f"SYS-{adr_id.replace('ADR-PS-', '')}"

    def _append_source_ref(self, entity: NormalizedEntity, ref: SourceRef) -> None:
        existing = {(item.source_ref, item.mention_role) for item in entity.source_refs}
        key = (ref.source_ref, ref.mention_role)
        if key not in existing:
            entity.source_refs.append(ref)
            entity.source_refs.sort(key=lambda item: (item.source_ref, item.mention_role))

    def _relationship_id(self, relationship_type: str, from_id: str, to_id: str) -> str:
        return f"{relationship_type}:{from_id}:{to_id}"

    def _add_relationship(
        self,
        relationships: Dict[str, RelationshipRecord],
        entities: Dict[str, NormalizedEntity],
        relationship_type: str,
        from_id: str,
        to_id: str,
        source_ref: str,
        evidence: Iterable[str],
        classification: str = "explicit",
        confidence: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> None:
        if from_id not in entities or to_id not in entities:
            return
        relationship_id = self._relationship_id(relationship_type, from_id, to_id)
        if relationship_id not in relationships:
            relationships[relationship_id] = RelationshipRecord(
                relationship_id=relationship_id,
                relationship_type=relationship_type,
                from_entity_id=from_id,
                to_entity_id=to_id,
                provenance_classification=classification,
                evidence=sorted(set(evidence)),
                canonical_source_ref=source_ref,
                confidence=confidence,
                metadata=metadata or {},
            )
        summary = getattr(entities[from_id].relationships, relationship_type)
        if to_id not in summary:
            summary.append(to_id)
            summary.sort()

    def _unresolved(
        self,
        items: List[UnresolvedRecord],
        gap_id: str,
        gap_class: str,
        gap_type: str,
        source_entity_id: str,
        severity: str,
        source_ref: str,
        evidence: list[str],
        related_entity_id: Optional[str] = None,
        expected_relationship: Optional[str] = None,
    ) -> None:
        items.append(
            UnresolvedRecord(
                id=gap_id,
                gap_class=gap_class,
                gap_type=gap_type,
                source_entity_id=source_entity_id,
                related_entity_id=related_entity_id,
                expected_relationship=expected_relationship,
                severity=severity,
                provenance=self._provenance("derived_registry", source_ref, "detect_unresolved", "derived"),
                evidence=evidence,
            )
        )

    def _classify_author_gap(self, gap) -> str:
        context = (getattr(gap, "context", None) or "").lower()
        if "classification: deferred" in context:
            return "author_declared_deferred_gap"
        if "classification: resolved" in context:
            return "author_declared_resolved_gap"
        return "author_declared_real_gap"

    def _validate_bundle(
        self,
        entity_registry: NormalizedEntityRegistry,
        relationship_registry: RelationshipRegistry,
        unresolved_registry: UnresolvedRegistry,
    ) -> None:
        self.diagnostics.clear()
        result = validate_bundle(
            entity_registry,
            relationship_registry,
            unresolved_registry,
            diagnostics=self.diagnostics,
        )
        if not result.is_valid:
            error = result.first_error
            raise ValueError(error.message if error is not None else "Bundle validation failed")

    def _legacy_entity(self, entity: NormalizedEntity) -> Optional[Entity]:
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
            related_adrs=sorted({
                ref.source_ref.split("#")[0]
                for ref in entity.source_refs
                if ref.source_ref.startswith("ADR-")
            }),
            relationships=EntityRelationships(
                depends_on=list(entity.relationships.related_to),
                implements=list(entity.relationships.enables),
                realizes=list(entity.relationships.enforces),
            ),
        )

    def generate_from_directory(self, adr_dir: Path, scope: Optional[ProjectScope] = None) -> ArchitectureDiscoveryBundle:
        self.diagnostics.clear()
        adr_dir = Path(adr_dir).resolve()
        scope = scope or self.scope_resolver.resolve(adr_dir.parent)
        namespace = self._load_namespace(scope)
        logical_files, physical_files, invariant_files = self._discover_source_files(adr_dir)

        logical_adrs: List[Tuple[LogicalADR, Path]] = [(self.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
        physical_adrs: List[Tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]] = [(self.parser.parse_adr(path), path.resolve()) for path in physical_files]
        standalone_invariants: List[Tuple[StandaloneInvariant, Path]] = [(self.parser.parse_invariant(path), path.resolve()) for path in invariant_files]

        coverage = SourceCoverageSummary(
            logical_adrs=len(logical_adrs),
            physical_adrs=sum(1 for adr, _ in physical_adrs if isinstance(adr, PhysicalADR)),
            physical_system_adrs=sum(1 for adr, _ in physical_adrs if isinstance(adr, PhysicalSystemADR)),
            physical_component_adrs=sum(1 for adr, _ in physical_adrs if isinstance(adr, PhysicalComponentADR)),
            standalone_invariants=len(standalone_invariants),
        )

        entities: Dict[str, NormalizedEntity] = {}
        relationships: Dict[str, RelationshipRecord] = {}
        unresolved: List[UnresolvedRecord] = []
        invariant_mentions: Dict[str, List[tuple[dict, str, str]]] = {}
        system_ids: Dict[str, str] = {}

        def add_entity(entity: NormalizedEntity, allow_reference_merge: bool = False) -> None:
            existing = entities.get(entity.id)
            if existing is None:
                entities[entity.id] = entity
                return
            if allow_reference_merge:
                self._append_source_ref(
                    existing,
                    SourceRef(
                        source_type=entity.canonical_source.source_type,
                        source_ref=entity.canonical_source.source_ref,
                        artifact_path=entity.canonical_source.artifact_path,
                        mention_role="reference",
                    ),
                )
                return
            raise ValueError(f"Duplicate canonical entity ID {entity.id}")

        def collect_standalone_invariant_mentions(mentions: Dict[str, List[tuple[dict, str, str]]]) -> None:
            for invariant, path in standalone_invariants:
                artifact = self._source_path(scope, path)
                mentions.setdefault(invariant.id, []).append((
                    {
                        "name": invariant.id,
                        "summary": self._summary(invariant.statement),
                        "metadata": {
                            "defined_in": invariant.defined_in,
                            "scope": invariant.scope,
                            "statement": invariant.statement,
                            "enforcement_level": invariant.enforcement_level.value,
                            "declaration_mode": invariant.declaration_mode or "canonical",
                            "upheld_by_decisions": list(invariant.upheld_by_decisions),
                            "enforced_by": list(invariant.enforced_by),
                        },
                    },
                    artifact,
                    invariant.id,
                ))

        self.pass_runner.run(
            logical_adrs=logical_adrs,
            physical_adrs=physical_adrs,
            standalone_invariants=standalone_invariants,
            entities=entities,
            relationships=relationships,
            unresolved=unresolved,
            system_ids=system_ids,
            source_path=lambda file_path: self._source_path(scope, file_path),
            canonical=self._canonical,
            provenance=self._provenance,
            summary=self._summary,
            complete=self._complete,
            classify_author_gap=self._classify_author_gap,
            system_entity_id=self._system_entity_id,
            relationship_id=self._relationship_id,
            add_entity=add_entity,
            append_source_ref=self._append_source_ref,
            collect_standalone_invariant_mentions=collect_standalone_invariant_mentions,
        )

        entity_registry = NormalizedEntityRegistry(entities=sorted(entities.values(), key=lambda item: (item.entity_type, item.id)))
        relationship_registry = RelationshipRegistry(relationships=sorted(relationships.values(), key=lambda item: item.relationship_id))
        unresolved_registry = UnresolvedRegistry(unresolved=sorted(unresolved, key=lambda item: item.id))
        decision_registry = self._filtered(entity_registry, "decision")
        capability_registry = self._filtered(entity_registry, "capability")
        invariant_registry = self._filtered(entity_registry, "invariant")
        component_registry = self._filtered(entity_registry, "component")
        system_registry = self._filtered(entity_registry, "system")
        legacy_entities = [item for item in (self._legacy_entity(entity) for entity in entity_registry.entities) if item is not None]
        legacy_registry = EntityRegistry(entities=sorted(legacy_entities, key=lambda item: item.entity_id))
        self.diagnostics.clear()
        validation = self.pass_runner.validate(
            entity_registry,
            relationship_registry,
            unresolved_registry,
            diagnostics=self.diagnostics,
        )
        if not validation.is_valid:
            error = validation.first_error
            raise ValueError(error.message if error is not None else "Bundle validation failed")
        index = ArchitectureIndex(
            architecture_namespace=namespace,
            generated_at=datetime.now(timezone.utc).replace(microsecond=0),
            generator=GENERATOR_ID,
            entity_registry_path="adrs/index/entity-registry.yaml",
            relationship_registry_path="adrs/index/relationship-registry.yaml",
            unresolved_registry_path="adrs/index/unresolved-registry.yaml",
            decision_registry_path="adrs/index/decision-registry.yaml",
            capability_registry_path="adrs/index/capability-registry.yaml",
            invariant_registry_path="adrs/index/invariant-registry.yaml",
            component_registry_path="adrs/index/component-registry.yaml",
            system_registry_path="adrs/index/system-registry.yaml",
            validation_summary=ValidationSummary(hard_failures=0, warnings=0, unresolved_entries=len(unresolved_registry.unresolved)),
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

    def generate_from_scope(self, scope: Optional[ProjectScope] = None) -> ArchitectureDiscoveryBundle:
        scope = scope or self.scope_resolver.resolve()
        return self.generate_from_directory(scope.adr_dir, scope)

    def render_yaml(self, model) -> str:
        return yaml.safe_dump(model.model_dump(mode="json", exclude_none=True), sort_keys=False, allow_unicode=True)

    def save_bundle(self, bundle: ArchitectureDiscoveryBundle, scope: Optional[ProjectScope] = None) -> dict[str, Path]:
        scope = scope or self.scope_resolver.resolve()
        index_dir = scope.adr_dir / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "architecture_index": index_dir / "architecture-index.yaml",
            "entity_registry": index_dir / "entity-registry.yaml",
            "relationship_registry": index_dir / "relationship-registry.yaml",
            "unresolved_registry": index_dir / "unresolved-registry.yaml",
            "decision_registry": index_dir / "decision-registry.yaml",
            "capability_registry": index_dir / "capability-registry.yaml",
            "invariant_registry": index_dir / "invariant-registry.yaml",
            "component_registry": index_dir / "component-registry.yaml",
            "system_registry": index_dir / "system-registry.yaml",
            "legacy_entity_registry": scope.adr_dir / "entities" / "registry.yaml",
        }
        payloads = {
            "architecture_index": bundle.architecture_index,
            "entity_registry": bundle.entity_registry,
            "relationship_registry": bundle.relationship_registry,
            "unresolved_registry": bundle.unresolved_registry,
            "decision_registry": bundle.decision_registry,
            "capability_registry": bundle.capability_registry,
            "invariant_registry": bundle.invariant_registry,
            "component_registry": bundle.component_registry,
            "system_registry": bundle.system_registry,
            "legacy_entity_registry": bundle.legacy_entity_registry,
        }
        for key, path in paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.render_yaml(payloads[key]), encoding="utf-8", newline="\n")
        return paths
