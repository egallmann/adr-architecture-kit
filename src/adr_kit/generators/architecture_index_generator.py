"""Architecture discovery generator for normalized index artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ..decorators import implements_adr
from ..compiler.diagnostics import DiagnosticLevel, DiagnosticLog
from ..compiler.frontend.parser import CachedADRParser
from ..compiler.frontend.support import (
    classify_author_gap,
    discover_source_files,
    load_namespace,
    make_canonical,
    make_completeness,
    make_provenance,
    source_path,
    summarize_text,
    system_entity_id,
)
from ..compiler.registry_bundle import (
    ArchitectureDiscoveryBundle,
    assemble_registry_bundle,
    render_bundle_yaml,
    render_legacy_entity_registry as render_legacy_entity_registry_output,
)
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


@implements_adr("ADR-L-0009", "ADR-L-0013", "ADR-PC-0001")
class ArchitectureIndexGenerator:
    """Generate normalized architecture discovery artifacts."""

    def __init__(self, parser: ADRParser | CachedADRParser = None, scope_resolver: ProjectScopeResolver = None):
        self.parser = parser if isinstance(parser, CachedADRParser) else CachedADRParser(parser or ADRParser())
        self.diagnostics = DiagnosticLog()
        self.pass_runner = FixedOrderArchitecturePassRunner()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()

    def _discover_source_files(self, adr_dir: Path) -> tuple[list[Path], list[Path], list[Path]]:
        return discover_source_files(adr_dir)

    def _source_path(self, scope: ProjectScope, file_path: Path) -> str:
        return source_path(scope, file_path)

    def _load_namespace(self, scope: ProjectScope) -> str:
        return load_namespace(self.parser, scope)

    def _provenance(self, source_type: str, source_ref: str, phase: str, classification: str) -> DiscoveryProvenance:
        return make_provenance(source_type, source_ref, phase, classification)

    def _canonical(self, source_type: str, source_ref: str, artifact_path: str) -> CanonicalSource:
        return make_canonical(source_type, source_ref, artifact_path)

    def _complete(self, missing_fields: Optional[list[str]] = None) -> Completeness:
        return make_completeness(missing_fields)

    def _summary(self, text: str, limit: int = 220) -> str:
        return summarize_text(text, limit)

    def _filtered(self, registry: NormalizedEntityRegistry, entity_type: str) -> NormalizedEntityRegistry:
        return NormalizedEntityRegistry(entities=[e for e in registry.entities if e.entity_type == entity_type])

    def _system_entity_id(self, adr_id: str) -> str:
        return system_entity_id(adr_id)

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
        return classify_author_gap(gap)

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
        from ..compiler.frontend import ArchModelBuilder

        builder = ArchModelBuilder(
            parser=self.parser,
            scope_resolver=self.scope_resolver,
            diagnostics=self.diagnostics,
        )
        build_result = builder.build_from_scope(scope)
        generated_at = datetime.now(timezone.utc).replace(microsecond=0)
        build_result.model.metadata.scope_root = str(scope.root)
        build_result.model.metadata.generated_at = generated_at
        bundle = assemble_registry_bundle(
            build_result.model,
            coverage=build_result.coverage,
            namespace=build_result.namespace,
            generated_at=generated_at,
            diagnostics=self.diagnostics,
            generator_id=GENERATOR_ID,
        )
        errors = [item for item in self.diagnostics.as_list() if item.level == DiagnosticLevel.ERROR]
        if errors:
            raise ValueError(errors[0].message)
        return bundle

    def generate_from_scope(self, scope: Optional[ProjectScope] = None) -> ArchitectureDiscoveryBundle:
        scope = scope or self.scope_resolver.resolve()
        return self.generate_from_directory(scope.adr_dir, scope)

    def render_yaml(self, model) -> str:
        return render_bundle_yaml(model)

    def render_legacy_entity_registry(self, bundle: ArchitectureDiscoveryBundle, scope: ProjectScope) -> str:
        return render_legacy_entity_registry_output(bundle, scope)

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
            if key == "legacy_entity_registry":
                path.write_text(self.render_legacy_entity_registry(bundle, scope), encoding="utf-8", newline="\n")
                continue
            path.write_text(self.render_yaml(payloads[key]), encoding="utf-8", newline="\n")
        return paths
