"""Frontend builder for the compiler IR."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from ...generators.architecture_index_generator import GENERATOR_ID, ArchitectureIndexGenerator
from ...models import CanonicalSource, DiscoveryProvenance, SourceCoverageSummary, SourceRef
from ...scope import ProjectScope, ProjectScopeResolver
from ..config import CompilerConfig
from ..diagnostics import DiagnosticLog
from ..ir import ArchModel, IREntity, IRRelationship, IRUnresolved
from .parser import CachedADRParser


@dataclass
class FrontendBuildResult:
    """Output of a frontend build."""

    model: ArchModel
    coverage: SourceCoverageSummary
    namespace: str


class ArchModelBuilder:
    """Build compiler IR from canonical ADR sources."""

    def __init__(
        self,
        parser: CachedADRParser | None = None,
        scope_resolver: ProjectScopeResolver | None = None,
        config: CompilerConfig | None = None,
        diagnostics: DiagnosticLog | None = None,
    ) -> None:
        self.parser = parser or CachedADRParser()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()
        self.config = config or CompilerConfig()
        self.diagnostics = diagnostics or DiagnosticLog()
        self._generator_helpers = ArchitectureIndexGenerator(parser=self.parser, scope_resolver=self.scope_resolver)

    def discover_source_files(self, adr_dir: Path) -> tuple[list[Path], list[Path], list[Path]]:
        return self._generator_helpers._discover_source_files(adr_dir)

    def build_from_scope(self, scope: ProjectScope | None = None) -> FrontendBuildResult:
        scope = scope or self.scope_resolver.resolve()
        return self.build_from_directory(scope.adr_dir, scope)

    def build_from_directory(self, adr_dir: Path, scope: ProjectScope | None = None) -> FrontendBuildResult:
        adr_dir = Path(adr_dir).resolve()
        scope = scope or self.scope_resolver.resolve(adr_dir.parent)
        namespace = self._generator_helpers._load_namespace(scope)
        logical_files, physical_files, invariant_files = self.discover_source_files(adr_dir)

        model = ArchModel()
        model.metadata.scope_root = str(scope.root)
        model.metadata.generator = GENERATOR_ID
        model.metadata.generated_at = None
        model.diagnostics = self.diagnostics.as_list()

        logical_adrs = [(self.parser.parse_logical_adr(path), path.resolve()) for path in logical_files]
        physical_adrs = [(self.parser.parse_adr(path), path.resolve()) for path in physical_files]
        standalone_invariants = [(self.parser.parse_invariant(path), path.resolve()) for path in invariant_files]

        for artifact, path in [*logical_adrs, *physical_adrs, *standalone_invariants]:
            model.corpus.add(path, artifact)

        coverage = SourceCoverageSummary(
            logical_adrs=len(logical_adrs),
            physical_adrs=sum(1 for adr, _ in physical_adrs if adr.__class__.__name__ == "PhysicalADR"),
            physical_system_adrs=sum(1 for adr, _ in physical_adrs if adr.__class__.__name__ == "PhysicalSystemADR"),
            physical_component_adrs=sum(1 for adr, _ in physical_adrs if adr.__class__.__name__ == "PhysicalComponentADR"),
            standalone_invariants=len(standalone_invariants),
        )

        invariant_mentions: Dict[str, List[tuple[dict, str, str]]] = {}
        system_ids: Dict[str, str] = {}
        reference_source_refs: Dict[str, list[SourceRef]] = {}

        def add_entity(entity: IREntity, allow_reference_merge: bool = False) -> None:
            existing = model.entities.get(entity.id)
            if existing is None:
                model.entities.add(entity)
                return
            if not allow_reference_merge:
                raise ValueError(f"Duplicate canonical entity ID {entity.id}")

            refs = reference_source_refs.setdefault(entity.id, [])
            ref = SourceRef(
                source_type=entity.canonical_source.source_type,
                source_ref=entity.canonical_source.source_ref,
                artifact_path=entity.canonical_source.artifact_path,
                mention_role="reference",
            )
            if (ref.source_ref, ref.mention_role) not in {(item.source_ref, item.mention_role) for item in refs}:
                refs.append(ref)
                refs.sort(key=lambda item: (item.source_ref, item.mention_role))

        for adr, path in logical_adrs:
            artifact = self._generator_helpers._source_path(scope, path)
            add_entity(
                IREntity(
                    id=adr.id,
                    entity_type="adr",
                    name=adr.title,
                    summary=self._generator_helpers._summary(adr.context),
                    canonical_source=self._generator_helpers._canonical("logical_adr", adr.id, artifact),
                    metadata={"status": adr.status.value, "domains": list(adr.domains), "tags": list(adr.tags)},
                    completeness=self._generator_helpers._complete(),
                    provenance=self._generator_helpers._provenance("logical_adr", adr.id, "extract_adr", "explicit"),
                )
            )
            for capability in adr.capabilities:
                source_ref = f"{adr.id}#{capability.id}"
                add_entity(
                    IREntity(
                        id=capability.id,
                        entity_type="capability",
                        name=capability.name,
                        summary=self._generator_helpers._summary(capability.description),
                        canonical_source=self._generator_helpers._canonical("logical_adr", source_ref, artifact),
                        metadata={
                            "adr_id": adr.id,
                            "domains": list(adr.domains),
                            "implemented_by_components": list(capability.implemented_by_components),
                            "enabled_by_decisions": list(capability.enabled_by_decisions),
                        },
                        completeness=self._generator_helpers._complete(),
                        provenance=self._generator_helpers._provenance("logical_adr", source_ref, "extract_capability", "explicit"),
                    )
                )
            for decision in adr.decisions:
                source_ref = f"{adr.id}#{decision.id}"
                add_entity(
                    IREntity(
                        id=decision.id,
                        entity_type="decision",
                        name=decision.summary,
                        summary=self._generator_helpers._summary(decision.rationale),
                        canonical_source=self._generator_helpers._canonical("logical_adr", source_ref, artifact),
                        metadata={
                            "adr_id": adr.id,
                            "related_invariants": list(decision.related_invariants),
                            "enforces_invariants": list(decision.enforces_invariants),
                            "enables_capabilities": list(decision.enables_capabilities),
                            "governs_components": list(decision.governs_components),
                            "supersedes": list(decision.supersedes),
                            "refines": list(decision.refines),
                        },
                        completeness=self._generator_helpers._complete(),
                        provenance=self._generator_helpers._provenance("logical_adr", source_ref, "extract_decision", "explicit"),
                    )
                )
            for invariant in adr.invariants:
                invariant_mentions.setdefault(invariant.id, []).append(
                    (
                        {
                            "name": invariant.id,
                            "summary": self._generator_helpers._summary(invariant.statement),
                            "metadata": {
                                "adr_id": adr.id,
                                "scope": invariant.scope,
                                "statement": invariant.statement,
                                "enforcement_level": invariant.enforcement_level.value,
                                "declaration_mode": invariant.declaration_mode or "local",
                                "upheld_by_decisions": list(invariant.upheld_by_decisions),
                            },
                        },
                        artifact,
                        f"{adr.id}#{invariant.id}",
                    )
                )
            for gap in adr.gaps:
                unresolved = self._make_unresolved(
                    gap_id=f"UGAP-{adr.id}-{gap.id}",
                    gap_class="author_declared",
                    gap_type=self._generator_helpers._classify_author_gap(gap),
                    source_entity_id=adr.id,
                    severity="important" if gap.blocking else "advisory",
                    source_ref=f"{adr.id}#{gap.id}",
                    evidence=[adr.id, gap.question],
                    classification="explicit",
                )
                model.unresolved.add(unresolved)

        for invariant, path in standalone_invariants:
            artifact = self._generator_helpers._source_path(scope, path)
            invariant_mentions.setdefault(invariant.id, []).append(
                (
                    {
                        "name": invariant.id,
                        "summary": self._generator_helpers._summary(invariant.statement),
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
                )
            )

        for inv_id, mentions in invariant_mentions.items():
            standalone = [item for item in mentions if item[2] == inv_id]
            local = [item for item in mentions if item[2] != inv_id]
            if len(standalone) > 1 or (not standalone and len(local) > 1):
                raise ValueError(f"Duplicate canonical invariant ID {inv_id}")
            payload, artifact, source_ref = standalone[0] if standalone else local[0]
            entity = IREntity(
                id=inv_id,
                entity_type="invariant",
                name=payload["name"],
                summary=payload["summary"],
                canonical_source=self._generator_helpers._canonical(
                    "standalone_invariant" if standalone else "logical_adr",
                    source_ref,
                    artifact,
                ),
                metadata=payload["metadata"],
                completeness=self._generator_helpers._complete(),
                provenance=self._generator_helpers._provenance(
                    "standalone_invariant" if standalone else "logical_adr",
                    source_ref,
                    "assign_canonical_invariant",
                    "explicit",
                ),
            )
            add_entity(entity)
            refs = reference_source_refs.setdefault(inv_id, [])
            for _, ref_artifact, ref_source in mentions:
                if ref_source == source_ref and ref_artifact == artifact:
                    continue
                ref = SourceRef(
                    source_type="logical_adr" if ref_source.startswith("ADR-") else "standalone_invariant",
                    source_ref=ref_source,
                    artifact_path=ref_artifact,
                    mention_role="reference",
                )
                if (ref.source_ref, ref.mention_role) not in {(item.source_ref, item.mention_role) for item in refs}:
                    refs.append(ref)
                    refs.sort(key=lambda item: (item.source_ref, item.mention_role))

        for adr, path in physical_adrs:
            artifact = self._generator_helpers._source_path(scope, path)
            source_type = (
                "physical_component_adr"
                if adr.__class__.__name__ == "PhysicalComponentADR"
                else "physical_system_adr"
                if adr.__class__.__name__ == "PhysicalSystemADR"
                else "physical_adr"
            )
            add_entity(
                IREntity(
                    id=adr.id,
                    entity_type="adr",
                    name=adr.title,
                    summary=self._generator_helpers._summary(adr.context),
                    canonical_source=self._generator_helpers._canonical(source_type, adr.id, artifact),
                    metadata={"status": adr.status.value, "domains": list(adr.domains), "tags": list(adr.tags)},
                    completeness=self._generator_helpers._complete(),
                    provenance=self._generator_helpers._provenance(source_type, adr.id, "extract_adr", "explicit"),
                ),
                allow_reference_merge=True,
            )
            if adr.__class__.__name__ == "PhysicalSystemADR":
                system_id = self._generator_helpers._system_entity_id(adr.id)
                system_ids[adr.id] = system_id
                add_entity(
                    IREntity(
                        id=system_id,
                        entity_type="system",
                        name=adr.title,
                        summary=self._generator_helpers._summary(adr.context),
                        canonical_source=self._generator_helpers._canonical("physical_system_adr", adr.id, artifact),
                        metadata={
                            "adr_id": adr.id,
                            "implements_logical": list(adr.implements_logical),
                            "technologies": list(adr.technologies),
                        },
                        completeness=self._generator_helpers._complete(),
                        provenance=self._generator_helpers._provenance("physical_system_adr", adr.id, "extract_system", "explicit"),
                    )
                )
            if adr.__class__.__name__ == "PhysicalComponentADR":
                for component in adr.component_specifications:
                    component_id = component.component_id or component.id
                    add_entity(
                        IREntity(
                            id=component_id,
                            entity_type="component",
                            name=component.name,
                            summary=self._generator_helpers._summary(component.responsibilities),
                            canonical_source=self._generator_helpers._canonical(
                                "physical_component_adr",
                                f"{adr.id}#{component_id}",
                                artifact,
                            ),
                            metadata={
                                "adr_id": adr.id,
                                "legacy_component_id": component.id,
                                "technologies": list(adr.technologies),
                                "module_path": component.implementation_identifiers.module_path,
                                "implements_capabilities": list(component.implements_capabilities),
                                "implements_system": list(adr.implements_system),
                            },
                            completeness=self._generator_helpers._complete(),
                            provenance=self._generator_helpers._provenance(
                                "physical_component_adr",
                                f"{adr.id}#{component_id}",
                                "extract_component",
                                "explicit",
                            ),
                        )
                    )

        for entity in model.entities.values():
            if entity.entity_type != "adr":
                adr_id = entity.canonical_source.source_ref.split("#")[0]
                if model.entities.get(adr_id) is not None:
                    model.relationships.add(
                        IRRelationship(
                            relationship_type="declared_in",
                            from_entity_id=entity.id,
                            to_entity_id=adr_id,
                            canonical_source_ref=entity.canonical_source.source_ref,
                            evidence=[entity.canonical_source.source_ref],
                        )
                    )

        for adr, _ in logical_adrs:
            for related in adr.related_adrs:
                if model.entities.get(related) is not None:
                    self._add_relationship(model, "references", adr.id, related, adr.id, [adr.id])
            for capability in adr.capabilities:
                for component_id in capability.implemented_by_components:
                    if model.entities.get(component_id) is not None:
                        self._add_relationship(model, "implemented_by", capability.id, component_id, f"{adr.id}#{capability.id}", [adr.id])
                    else:
                        model.unresolved.add(
                            self._make_unresolved(
                                gap_id=f"GAP-IMPL-{capability.id}-{component_id}",
                                gap_class="generator_derived",
                                gap_type="capability_without_implementing_component",
                                source_entity_id=capability.id,
                                severity="important",
                                source_ref=f"{adr.id}#{capability.id}",
                                evidence=[adr.id, component_id],
                                related_entity_id=component_id,
                                expected_relationship="implemented_by",
                            )
                        )
            for decision in adr.decisions:
                for invariant_id in sorted(set(decision.related_invariants + decision.enforces_invariants)):
                    if model.entities.get(invariant_id) is not None:
                        self._add_relationship(model, "enforces", decision.id, invariant_id, f"{adr.id}#{decision.id}", [adr.id])
                    else:
                        model.unresolved.add(
                            self._make_unresolved(
                                gap_id=f"GAP-INV-{decision.id}-{invariant_id}",
                                gap_class="generator_derived",
                                gap_type="unresolved_reference",
                                source_entity_id=decision.id,
                                severity="important",
                                source_ref=f"{adr.id}#{decision.id}",
                                evidence=[adr.id, invariant_id],
                                related_entity_id=invariant_id,
                                expected_relationship="enforces",
                            )
                        )
                for capability_id in decision.enables_capabilities:
                    if model.entities.get(capability_id) is not None:
                        self._add_relationship(model, "enables", decision.id, capability_id, f"{adr.id}#{decision.id}", [adr.id])
                        self._add_relationship(
                            model,
                            "enabled_by",
                            capability_id,
                            decision.id,
                            f"{adr.id}#{decision.id}",
                            [adr.id],
                            classification="derived",
                        )
                    else:
                        model.unresolved.add(
                            self._make_unresolved(
                                gap_id=f"GAP-CAP-{decision.id}-{capability_id}",
                                gap_class="generator_derived",
                                gap_type="unresolved_reference",
                                source_entity_id=decision.id,
                                severity="important",
                                source_ref=f"{adr.id}#{decision.id}",
                                evidence=[adr.id, capability_id],
                                related_entity_id=capability_id,
                                expected_relationship="enables",
                            )
                        )
                for component_id in decision.governs_components:
                    if model.entities.get(component_id) is not None:
                        self._add_relationship(model, "governs", decision.id, component_id, f"{adr.id}#{decision.id}", [adr.id])
                for target in decision.supersedes:
                    if model.entities.get(target) is not None:
                        self._add_relationship(model, "supersedes", decision.id, target, f"{adr.id}#{decision.id}", [adr.id])
                        self._add_relationship(model, "superseded_by", target, decision.id, f"{adr.id}#{decision.id}", [adr.id], classification="derived")
                for target in decision.refines:
                    if model.entities.get(target) is not None:
                        self._add_relationship(model, "refines", decision.id, target, f"{adr.id}#{decision.id}", [adr.id])

        for invariant, _ in standalone_invariants:
            if model.entities.get(invariant.id) is None:
                continue
            for target in invariant.enforced_by:
                if model.entities.get(target) is not None:
                    self._add_relationship(model, "enforces", invariant.id, target, invariant.id, [invariant.id])

        for adr, _ in physical_adrs:
            if adr.__class__.__name__ == "PhysicalComponentADR":
                for component in adr.component_specifications:
                    component_id = component.component_id or component.id
                    for capability_id in component.implements_capabilities:
                        if model.entities.get(capability_id) is not None:
                            self._add_relationship(model, "implemented_by", capability_id, component_id, f"{adr.id}#{component_id}", [adr.id])
                        else:
                            model.unresolved.add(
                                self._make_unresolved(
                                    gap_id=f"GAP-MISSING-CAP-{component_id}-{capability_id}",
                                    gap_class="generator_derived",
                                    gap_type="unresolved_reference",
                                    source_entity_id=component_id,
                                    severity="important",
                                    source_ref=f"{adr.id}#{component_id}",
                                    evidence=[adr.id, capability_id],
                                    related_entity_id=capability_id,
                                    expected_relationship="implemented_by",
                                )
                            )
                    for system_id in adr.implements_system:
                        resolved_system_id = system_ids.get(system_id, self._generator_helpers._system_entity_id(system_id))
                        if model.entities.get(resolved_system_id) is not None:
                            self._add_relationship(model, "embodied_in", component_id, resolved_system_id, f"{adr.id}#{component_id}", [adr.id])
                        else:
                            model.unresolved.add(
                                self._make_unresolved(
                                    gap_id=f"GAP-MISSING-SYS-{component_id}-{system_id}",
                                    gap_class="generator_derived",
                                    gap_type="component_without_system",
                                    source_entity_id=component_id,
                                    severity="important",
                                    source_ref=f"{adr.id}#{component_id}",
                                    evidence=[adr.id, system_id],
                                    related_entity_id=system_id,
                                    expected_relationship="embodied_in",
                                )
                            )
                    for dep in component.dependencies:
                        if model.entities.get(dep) is not None:
                            self._add_relationship(
                                model,
                                "related_to",
                                component_id,
                                dep,
                                f"{adr.id}#{component_id}",
                                [adr.id],
                                classification="derived",
                                confidence=0.8,
                            )
            if adr.__class__.__name__ == "PhysicalSystemADR" and adr.references_components:
                for component_adr in adr.references_components:
                    if model.entities.get(component_adr) is not None:
                        self._add_relationship(model, "related_to", adr.id, component_adr, adr.id, [adr.id], classification="derived", confidence=0.8)

        for entity_id, refs in reference_source_refs.items():
            entity = model.entities.get(entity_id)
            if entity is not None:
                entity.source_refs.extend(refs)
                entity.source_refs.sort(key=lambda item: (item.source_ref, item.mention_role))

        model.corpus.add(scope.root / "PROJECT.yaml", self.parser.parse_yaml(scope.root / "PROJECT.yaml"))
        model.entities.add(
            IREntity(
                id=f"{namespace}:__namespace__",
                entity_type="boundary",
                name=namespace,
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
        return FrontendBuildResult(model=model, coverage=coverage, namespace=namespace)

    def _add_relationship(
        self,
        model: ArchModel,
        relationship_type: str,
        from_id: str,
        to_id: str,
        source_ref: str,
        evidence: list[str],
        *,
        classification: str = "explicit",
        confidence: float = 1.0,
    ) -> None:
        if model.entities.get(from_id) is None or model.entities.get(to_id) is None:
            return
        model.relationships.add(
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

    def _make_unresolved(
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
        provenance = self._generator_helpers._provenance("derived_registry", source_ref, "detect_unresolved", classification)
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


def build_arch_model(
    scope: ProjectScope | None = None,
    *,
    parser: CachedADRParser | None = None,
    scope_resolver: ProjectScopeResolver | None = None,
    config: CompilerConfig | None = None,
    diagnostics: DiagnosticLog | None = None,
) -> FrontendBuildResult:
    """Build an ArchModel for the provided scope."""

    builder = ArchModelBuilder(
        parser=parser,
        scope_resolver=scope_resolver,
        config=config,
        diagnostics=diagnostics,
    )
    return builder.build_from_scope(scope)
