"""Explicit compiler pipeline for ADR discovery compilation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Protocol, cast

from ..decorators import implements_adr
from ..identity import UUIDV7_PATTERN
from ..models import (
    CanonicalSource,
    DiscoveryProvenance,
    NormalizedEntityRegistry,
    RelationshipRegistry,
    SourceCoverageSummary,
    SourceRef,
    UnresolvedRegistry,
)
from ..scope import ProjectScope
from .backend.projection import project_entity, project_relationship, project_unresolved
from .config import CompilerConfig
from .diagnostics import DiagnosticLog
from .frontend.adr_access import (
    is_physical_adr,
    is_physical_component_adr,
    is_physical_system_adr,
)
from .frontend.parser import CachedADRParser
from .frontend.support import (
    GENERATOR_ID,
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
from .ir import ArchModel, IREntity, IRRelationship, IRUnresolved
from .passes.detect_unresolved import detect_unresolved
from .passes.derive_relationships import derive_relationships
from .passes.extract_logical_entities import extract_logical_entities
from .passes.extract_physical_entities import extract_physical_entities
from .passes.extract_extension_entities import extract_extension_entities
from .passes.resolve_invariant_canonical import resolve_invariant_canonical
from .passes.validate_bundle import validate_bundle


class MixedSchemaVersionError(ValueError):
    """Raised when a scope mixes v1.3 and legacy schema versions."""


@dataclass
class FrontendBuildResult:
    """Output of a frontend pipeline run."""

    model: ArchModel
    coverage: SourceCoverageSummary
    namespace: str
    model_version: str = "1.1"


@dataclass
class CompilerPipelineState:
    """Mutable state carried through the ADR discovery pipeline."""

    scope: ProjectScope
    parser: CachedADRParser
    config: CompilerConfig
    diagnostics: DiagnosticLog
    model: ArchModel = field(default_factory=ArchModel)
    namespace: str = ""
    coverage: SourceCoverageSummary = field(
        default_factory=lambda: SourceCoverageSummary(
            logical_adrs=0,
            physical_adrs=0,
            physical_system_adrs=0,
            physical_component_adrs=0,
            standalone_invariants=0,
        )
    )
    detected_schema_versions: set[str] = field(default_factory=set)
    model_version: str = "1.1"
    logical_files: list[Path] = field(default_factory=list)
    physical_files: list[Path] = field(default_factory=list)
    invariant_files: list[Path] = field(default_factory=list)
    logical_adrs: list[tuple[object, Path]] = field(default_factory=list)
    physical_adrs: list[tuple[object, Path]] = field(default_factory=list)
    standalone_invariants: list[tuple[object, Path]] = field(default_factory=list)
    invariant_mentions: Dict[str, List[tuple[dict, str, str]]] = field(default_factory=dict)
    system_ids: Dict[str, str] = field(default_factory=dict)
    reference_source_refs: Dict[str, list[SourceRef]] = field(default_factory=dict)
    adr_uuid_map: Dict[str, str] = field(default_factory=dict)

    def initialize_model(self) -> None:
        self.model.metadata.scope_root = str(self.scope.root)
        self.model.metadata.generator = GENERATOR_ID
        self.model.metadata.generated_at = None
        self.model.diagnostics = self.diagnostics.as_list()

    def add_entity(self, entity: IREntity, allow_reference_merge: bool = False) -> None:
        existing = self.model.entities.get(entity.id)
        if existing is None:
            self.model.entities.add(entity)
            return
        if not allow_reference_merge:
            raise ValueError(f"Duplicate canonical entity ID {entity.id}")

        refs = self.reference_source_refs.setdefault(entity.id, [])
        ref = SourceRef(
            source_type=entity.canonical_source.source_type,
            source_ref=entity.canonical_source.source_ref,
            artifact_path=entity.canonical_source.artifact_path,
            mention_role="reference",
        )
        if (ref.source_ref, ref.mention_role) not in {
            (item.source_ref, item.mention_role) for item in refs
        }:
            refs.append(ref)
            refs.sort(key=lambda item: (item.source_ref, item.mention_role))

    def append_source_ref(self, entity: IREntity, ref: SourceRef) -> None:
        refs = self.reference_source_refs.setdefault(entity.id, [])
        if (ref.source_ref, ref.mention_role) not in {
            (item.source_ref, item.mention_role) for item in refs
        }:
            refs.append(ref)
            refs.sort(key=lambda item: (item.source_ref, item.mention_role))

    @staticmethod
    def relationship_id(relationship_type: str, from_id: str, to_id: str) -> str:
        return f"{relationship_type}:{from_id}:{to_id}"

    def add_relationship(
        self,
        relationship_type: str,
        from_id: str,
        to_id: str,
        source_ref: str,
        evidence: list[str],
        *,
        classification: str = "explicit",
        confidence: float = 1.0,
    ) -> None:
        if self.model.entities.get(from_id) is None or self.model.entities.get(to_id) is None:
            return
        self.model.relationships.add(
            IRRelationship(
                relationship_type=relationship_type,
                from_entity_id=from_id,
                to_entity_id=to_id,
                canonical_source_ref=source_ref,
                provenance_classification=classification,
                evidence=evidence,
                confidence=confidence,
            )
        )

    def make_unresolved(
        self,
        *,
        gap_id: str,
        gap_class: str,
        gap_type: str,
        source_entity_id: str,
        severity: str,
        source_ref: str,
        evidence: list[str],
        classification: str = "derived",
        related_entity_id: str | None = None,
        expected_relationship: str | None = None,
    ) -> IRUnresolved:
        provenance = make_provenance(
            "derived_registry", source_ref, "detect_unresolved", classification
        )
        return IRUnresolved(
            id=gap_id,
            gap_class=gap_class,
            gap_type=gap_type,
            source_entity_id=source_entity_id,
            related_entity_id=related_entity_id,
            expected_relationship=expected_relationship,
            severity=severity,
            provenance=provenance,
            evidence=evidence,
        )

    def collect_standalone_invariant_mentions(self) -> None:
        """Standalone invariant definition discovery is retired."""
        if self.standalone_invariants:
            raise ValueError(
                "STANDALONE_INVARIANT_AUTHORITY_RETIRED: standalone invariant definitions are not admitted"
            )

    def finalize_source_refs(self) -> None:
        for entity_id, refs in self.reference_source_refs.items():
            entity = self.model.entities.get(entity_id)
            if entity is None:
                continue
            entity.source_refs.extend(refs)
            entity.source_refs.sort(key=lambda item: (item.source_ref, item.mention_role))

    def add_namespace_boundary(self) -> None:
        self.model.corpus.add(
            self.scope.root / "PROJECT.yaml",
            self.parser.parse_yaml(self.scope.root / "PROJECT.yaml"),
        )
        self.model.entities.add(
            IREntity(
                id=f"{self.namespace}:__namespace__",
                entity_type="boundary",
                name=self.namespace,
                summary="Namespace marker for compiler build metadata.",
                canonical_source=CanonicalSource(
                    source_type="project_metadata",
                    source_ref="PROJECT.yaml#architecture_namespace",
                    artifact_path="PROJECT.yaml",
                ),
                provenance=DiscoveryProvenance(
                    source_type="project_metadata",
                    source_ref="PROJECT.yaml#architecture_namespace",
                    extraction_phase="load_namespace",
                    classification="explicit",
                    generator=GENERATOR_ID,
                ),
            )
        )


class CompilerPipelinePass(Protocol):
    """Deterministic pipeline pass interface."""

    name: str

    def run(self, state: CompilerPipelineState) -> None:
        """Mutate the compiler pipeline state."""


@dataclass(frozen=True)
class ADRParsePass:
    name: str = "adr_parse"

    def run(self, state: CompilerPipelineState) -> None:
        adr_dir = state.scope.adr_dir.resolve()
        logical_files, physical_files, invariant_files = discover_source_files(adr_dir)
        state.logical_files = logical_files
        state.physical_files = physical_files
        state.invariant_files = invariant_files
        state.logical_adrs = [
            (state.parser.parse_logical_adr(path), path.resolve()) for path in logical_files
        ]
        state.physical_adrs = [
            (state.parser.parse_adr(path), path.resolve()) for path in physical_files
        ]
        state.standalone_invariants = []

        for artifact, path in [
            *state.logical_adrs,
            *state.physical_adrs,
        ]:
            state.model.corpus.add(path, artifact)
            sv = getattr(artifact, "schema_version", "1.0")
            state.detected_schema_versions.add(sv)

        state.coverage = SourceCoverageSummary(
            logical_adrs=len(state.logical_adrs),
            physical_adrs=sum(1 for adr, _ in state.physical_adrs if is_physical_adr(adr)),
            physical_system_adrs=sum(
                1 for adr, _ in state.physical_adrs if is_physical_system_adr(adr)
            ),
            physical_component_adrs=sum(
                1 for adr, _ in state.physical_adrs if is_physical_component_adr(adr)
            ),
            standalone_invariants=0,
        )


@dataclass(frozen=True)
class VersionDetectionPass:
    name: str = "version_detection"

    def run(self, state: CompilerPipelineState) -> None:
        versions = state.detected_schema_versions
        authoring_versions = versions & {"1.3", "1.4"}
        has_v13 = "1.3" in authoring_versions
        has_v14 = "1.4" in authoring_versions
        has_legacy = bool(versions - {"1.3", "1.4"})

        if len(authoring_versions) > 1 or (authoring_versions and has_legacy):
            raise MixedSchemaVersionError(
                f"Scope mixes incompatible authoring schema versions "
                f"({', '.join(sorted(versions))}). "
                f"All ADRs must use the same schema line for compilation."
            )

        state.model_version = (
            "2.1" if has_v14 and not has_legacy else "2.0" if has_v13 else "1.1"
        )


@dataclass(frozen=True)
class ADRNormalizationPass:
    name: str = "adr_normalization"

    def run(self, state: CompilerPipelineState) -> None:
        state.initialize_model()
        state.namespace = load_namespace(state.parser, state.scope)


@dataclass(frozen=True)
class LogicalEntityExtractionPass:
    name: str = "logical_entity_extraction"

    def run(self, state: CompilerPipelineState) -> None:
        logical_extraction = extract_logical_entities(
            state.logical_adrs,
            source_path=lambda path: source_path(state.scope, path),
            canonical=make_canonical,
            provenance=make_provenance,
            summary=summarize_text,
            complete=make_completeness,
            classify_author_gap=classify_author_gap,
        )
        state.invariant_mentions = {
            inv_id: [
                (mention.payload, mention.artifact_path, mention.source_ref) for mention in mentions
            ]
            for inv_id, mentions in logical_extraction.invariant_mentions.items()
        }
        for extracted in logical_extraction.entities:
            if state.model_version in {"2.0", "2.1"}:
                alias_id = extracted.entity.id if not UUIDV7_PATTERN.match(extracted.entity.id) else None
                if alias_id is None:
                    for adr, _ in state.logical_adrs:
                        if getattr(adr, "id", None) == extracted.entity.id:
                            alias_id = getattr(adr, "alias_id", extracted.entity.id)
                            alias_name = getattr(adr, "alias_name", None)
                            if alias_name:
                                extracted.entity.metadata["alias_name"] = alias_name
                            break
                        for collection_name in ("capabilities", "decisions", "invariants", "architectural_boundaries", "interaction_contracts"):
                            for item in getattr(adr, collection_name, []):
                                if getattr(item, "id", None) == extracted.entity.id:
                                    alias_id = getattr(item, "alias_id", extracted.entity.id)
                                    alias_name = getattr(item, "alias_name", None)
                                    if alias_name:
                                        extracted.entity.metadata["alias_name"] = alias_name
                                    break
                            if alias_id and alias_id != extracted.entity.id:
                                break
                if alias_id:
                    extracted.entity.metadata["alias_id"] = alias_id
                    state.adr_uuid_map[alias_id] = extracted.entity.id
            state.add_entity(
                extracted.entity, allow_reference_merge=extracted.allow_reference_merge
            )
        for unresolved in logical_extraction.unresolved:
            state.model.unresolved.add(
                state.make_unresolved(
                    gap_id=unresolved.id,
                    gap_class=unresolved.gap_class,
                    gap_type=unresolved.gap_type,
                    source_entity_id=unresolved.source_entity_id,
                    severity=unresolved.severity,
                    source_ref=unresolved.provenance.source_ref,
                    evidence=list(unresolved.evidence),
                    classification=unresolved.provenance.classification,
                    related_entity_id=unresolved.related_entity_id,
                    expected_relationship=unresolved.expected_relationship,
                )
            )


@dataclass(frozen=True)
class InvariantExtractionPass:
    name: str = "invariant_extraction"

    def run(self, state: CompilerPipelineState) -> None:
        state.collect_standalone_invariant_mentions()
        invariant_resolution = resolve_invariant_canonical(
            state.invariant_mentions,
            canonical=make_canonical,
            provenance=make_provenance,
            complete=make_completeness,
        )
        for extracted in invariant_resolution.entities:
            if state.model_version in {"2.0", "2.1"}:
                metadata = extracted.entity.metadata
                alias_id = metadata.get("alias_id") if isinstance(metadata, dict) else None
                if isinstance(alias_id, str) and alias_id:
                    state.adr_uuid_map[alias_id] = extracted.entity.id
            state.add_entity(
                extracted.entity, allow_reference_merge=extracted.allow_reference_merge
            )
        for selection in invariant_resolution.selections.values():
            for ref in selection.reference_source_refs:
                state.append_source_ref(selection.entity, ref)


@dataclass(frozen=True)
class PhysicalEntityExtractionPass:
    name: str = "physical_entity_extraction"

    def run(self, state: CompilerPipelineState) -> None:
        # extract_physical_entities prefers authored v1.3 system.id; fallback mints SYS-*.
        physical_extraction = extract_physical_entities(
            state.physical_adrs,
            source_path=lambda path: source_path(state.scope, path),
            canonical=make_canonical,
            provenance=make_provenance,
            summary=summarize_text,
            complete=make_completeness,
            system_entity_id=system_entity_id,
        )
        for extracted in physical_extraction.entities:
            if state.model_version in {"2.0", "2.1"}:
                alias_id = self._extract_alias_id(extracted.entity)
                if alias_id:
                    extracted.entity.metadata["alias_id"] = alias_id
                    alias_name = self._extract_alias_name(extracted.entity)
                    if alias_name:
                        extracted.entity.metadata["alias_name"] = alias_name
                    state.adr_uuid_map[alias_id] = extracted.entity.id
            state.add_entity(
                extracted.entity, allow_reference_merge=extracted.allow_reference_merge
            )
        state.system_ids.update(physical_extraction.system_ids)

        if state.model_version in {"2.0", "2.1"}:
            for adr, _ in state.physical_adrs:
                if is_physical_system_adr(adr):
                    alias_id = getattr(adr, "alias_id", None)
                    if isinstance(alias_id, str) and alias_id:
                        state.adr_uuid_map[alias_id] = adr.id
                    authored = getattr(adr, "system", None)
                    if authored is not None:
                        sys_alias = getattr(authored, "alias_id", None)
                        sys_id = getattr(authored, "id", None)
                        if isinstance(sys_alias, str) and isinstance(sys_id, str):
                            state.adr_uuid_map[sys_alias] = sys_id

    @staticmethod
    def _extract_alias_id(entity: Any) -> str | None:
        metadata = getattr(entity, "metadata", None)
        if isinstance(metadata, dict) and "alias_id" in metadata:
            value = metadata["alias_id"]
            return value if isinstance(value, str) else None
        entity_id = getattr(entity, "id", "")
        if isinstance(entity_id, str) and not UUIDV7_PATTERN.match(entity_id):
            return entity_id
        return None

    @staticmethod
    def _extract_alias_name(entity: Any) -> str | None:
        metadata = getattr(entity, "metadata", None)
        if isinstance(metadata, dict) and "alias_name" in metadata:
            value = metadata["alias_name"]
            return value if isinstance(value, str) else None
        return None


@dataclass(frozen=True)
class ExtensionEntityExtractionPass:
    name: str = "extension_entity_extraction"

    def run(self, state: CompilerPipelineState) -> None:
        result = extract_extension_entities(
            [*state.logical_adrs, *state.physical_adrs],
            architecture_namespace=state.namespace,
            source_path=lambda path: source_path(state.scope, path),
            canonical=make_canonical,
            provenance=make_provenance,
        )
        for entity in result.entities:
            state.add_entity(entity)
        for relationship in result.relationships:
            if (
                state.model.entities.get(relationship.from_entity_id) is None
                or state.model.entities.get(relationship.to_entity_id) is None
            ):
                raise ValueError(
                    "Extension relationship endpoint does not resolve to a compiled entity: "
                    f"{relationship.from_entity_id} -> {relationship.to_entity_id}"
                )
            state.model.relationships.add(relationship)


@dataclass(frozen=True)
class RelationshipInferencePass:
    name: str = "relationship_inference"

    def run(self, state: CompilerPipelineState) -> None:
        result = derive_relationships(
            entities={
                entity.id: projected
                for entity in state.model.entities.values()
                if (projected := project_entity(entity, state.model.relationships)) is not None
            },
            logical_adrs=state.logical_adrs,
            standalone_invariants=state.standalone_invariants,
            physical_adrs=state.physical_adrs,
            system_ids=state.system_ids,
            relationship_id=state.relationship_id,
        )
        for item in result.relationships:
            owner_id = self._resolve_owner(state, item) if state.model_version in {"2.0", "2.1"} else None
            state.model.relationships.add(
                IRRelationship(
                    relationship_type=item.relationship_type,
                    from_entity_id=item.from_entity_id,
                    to_entity_id=item.to_entity_id,
                    canonical_source_ref=item.canonical_source_ref,
                    provenance_classification=item.provenance_classification,
                    evidence=list(item.evidence),
                    confidence=item.confidence,
                    metadata=dict(item.metadata),
                    assertion_id=item.assertion_id,
                    source_pointer=item.source_pointer,
                    source_owner_id=owner_id,
                )
            )
            if item.metadata.get("target_scope") in {"external", "expectation"}:
                continue
            source_entity = state.model.entities.get(item.from_entity_id)
            if source_entity is None:
                continue
            summary_list = getattr(source_entity.relationships, item.relationship_type)
            if item.to_entity_id not in summary_list:
                summary_list.append(item.to_entity_id)
                summary_list.sort()
        state._generator_gaps = result.generator_gaps

    @staticmethod
    def _resolve_owner(state: CompilerPipelineState, item: Any) -> str | None:
        ref = str(getattr(item, "canonical_source_ref", ""))
        adr_ref = ref.split("#")[0] if "#" in ref else ref
        if UUIDV7_PATTERN.match(adr_ref):
            return adr_ref
        entity = state.model.entities.get(adr_ref)
        if entity is not None and UUIDV7_PATTERN.match(entity.id):
            return entity.id
        return state.adr_uuid_map.get(adr_ref)


@dataclass(frozen=True)
class UnresolvedDetectionPass:
    name: str = "unresolved_detection"

    def run(self, state: CompilerPipelineState) -> None:
        result = detect_unresolved(
            getattr(state, "_generator_gaps", []),
            provenance=make_provenance,
        )
        for item in result.unresolved:
            state.model.unresolved.add(
                IRUnresolved(
                    id=item.id,
                    gap_class=item.gap_class,
                    gap_type=item.gap_type,
                    source_entity_id=item.source_entity_id,
                    related_entity_id=item.related_entity_id,
                    expected_relationship=item.expected_relationship,
                    severity=item.severity,
                    provenance=item.provenance,
                    evidence=list(item.evidence),
                    suggested_resolution=item.suggested_resolution,
                )
            )


@dataclass(frozen=True)
class ValidationPass:
    name: str = "validation"

    def run(self, state: CompilerPipelineState) -> None:
        state.finalize_source_refs()
        state.add_namespace_boundary()
        entity_registry = [
            projected
            for entity in state.model.entities.values()
            if (projected := project_entity(entity, state.model.relationships)) is not None
        ]
        relationship_registry = [
            project_relationship(item) for item in state.model.relationships.values()
        ]
        unresolved_registry = [project_unresolved(item) for item in state.model.unresolved.values()]
        result = validate_bundle(
            NormalizedEntityRegistry(entities=entity_registry),
            RelationshipRegistry(relationships=relationship_registry),
            UnresolvedRegistry(unresolved=unresolved_registry),
            diagnostics=state.diagnostics,
        )
        if not result.is_valid:
            error = result.first_error
            raise ValueError(error.message if error is not None else "Bundle validation failed")


@dataclass
@implements_adr("ADR-L-0009", "ADR-L-0013")
class CompilerPipeline:
    """Deterministic discovery pipeline over the existing compiler IR."""

    passes: list[CompilerPipelinePass]

    def run(self, state: CompilerPipelineState) -> FrontendBuildResult:
        for pipeline_pass in self.passes:
            pipeline_pass.run(state)
        return FrontendBuildResult(
            model=state.model,
            coverage=state.coverage,
            namespace=state.namespace,
            model_version=state.model_version,
        )


def build_default_frontend_pipeline() -> CompilerPipeline:
    """Build the canonical discovery pipeline used by the compiler frontend."""
    passes = cast(
        list[CompilerPipelinePass],
        [
            ADRParsePass(),
            VersionDetectionPass(),
            ADRNormalizationPass(),
            LogicalEntityExtractionPass(),
            InvariantExtractionPass(),
            PhysicalEntityExtractionPass(),
            ExtensionEntityExtractionPass(),
            RelationshipInferencePass(),
            UnresolvedDetectionPass(),
            ValidationPass(),
        ],
    )
    return CompilerPipeline(passes=passes)


@implements_adr("ADR-L-0009", "ADR-L-0013")
def run_frontend_pipeline(
    *,
    scope: ProjectScope,
    parser: CachedADRParser | None = None,
    config: CompilerConfig | None = None,
    diagnostics: DiagnosticLog | None = None,
    pipeline: CompilerPipeline | None = None,
) -> FrontendBuildResult:
    """Run the canonical frontend pipeline for one scope."""
    state = CompilerPipelineState(
        scope=scope,
        parser=parser or CachedADRParser(),
        config=config or CompilerConfig(),
        diagnostics=diagnostics or DiagnosticLog(),
    )
    return (pipeline or build_default_frontend_pipeline()).run(state)
