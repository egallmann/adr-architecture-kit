"""Minimal fixed-order compiler pass runner for generator migration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...models import (
    LogicalADR,
    NormalizedEntity,
    NormalizedEntityRegistry,
    PhysicalADR,
    PhysicalComponentADR,
    PhysicalSystemADR,
    RelationshipRecord,
    RelationshipRegistry,
    SourceRef,
    StandaloneInvariant,
    UnresolvedRecord,
    UnresolvedRegistry,
)
from .detect_unresolved import UnresolvedDetectionResult, detect_unresolved
from .derive_relationships import RelationshipDerivationResult, derive_relationships
from .extract_logical_entities import LogicalExtractionResult, extract_logical_entities
from .extract_physical_entities import PhysicalExtractionResult, extract_physical_entities
from .resolve_invariant_canonical import InvariantResolutionResult, resolve_invariant_canonical
from .validate_bundle import BundleValidationResult, validate_bundle


@dataclass
class FixedOrderPassRunResult:
    """Outputs from the fixed-order extraction sequence."""

    logical_extraction: LogicalExtractionResult
    invariant_resolution: InvariantResolutionResult
    physical_extraction: PhysicalExtractionResult
    relationship_derivation: RelationshipDerivationResult
    unresolved_detection: UnresolvedDetectionResult


@dataclass(frozen=True)
class FixedOrderArchitecturePassRunner:
    """Run the extracted compiler helpers in the current fixed generator order."""

    def run(
        self,
        *,
        logical_adrs: list[tuple[LogicalADR, Path]],
        physical_adrs: list[tuple[PhysicalADR | PhysicalSystemADR | PhysicalComponentADR, Path]],
        standalone_invariants: list[tuple[StandaloneInvariant, Path]],
        entities: dict[str, NormalizedEntity],
        relationships: dict[str, RelationshipRecord],
        unresolved: list[UnresolvedRecord],
        system_ids: dict[str, str],
        source_path,
        canonical,
        provenance,
        summary,
        complete,
        classify_author_gap,
        system_entity_id,
        relationship_id,
        add_entity,
        append_source_ref,
        collect_standalone_invariant_mentions,
    ) -> FixedOrderPassRunResult:
        logical_extraction = extract_logical_entities(
            logical_adrs,
            source_path=source_path,
            canonical=canonical,
            provenance=provenance,
            summary=summary,
            complete=complete,
            classify_author_gap=classify_author_gap,
        )
        invariant_mentions = {
            inv_id: [(mention.payload, mention.artifact_path, mention.source_ref) for mention in mentions]
            for inv_id, mentions in logical_extraction.invariant_mentions.items()
        }
        for extracted in logical_extraction.entities:
            add_entity(extracted.entity, allow_reference_merge=extracted.allow_reference_merge)
        unresolved.extend(logical_extraction.unresolved)

        collect_standalone_invariant_mentions(invariant_mentions)
        invariant_resolution = resolve_invariant_canonical(
            invariant_mentions,
            canonical=canonical,
            provenance=provenance,
            complete=complete,
        )
        for extracted in invariant_resolution.entities:
            add_entity(extracted.entity, allow_reference_merge=extracted.allow_reference_merge)
        for selection in invariant_resolution.selections.values():
            for ref in selection.reference_source_refs:
                append_source_ref(selection.entity, ref)

        physical_extraction = extract_physical_entities(
            physical_adrs,
            source_path=source_path,
            canonical=canonical,
            provenance=provenance,
            summary=summary,
            complete=complete,
            system_entity_id=system_entity_id,
        )
        for extracted in physical_extraction.entities:
            add_entity(extracted.entity, allow_reference_merge=extracted.allow_reference_merge)
        system_ids.update(physical_extraction.system_ids)

        relationship_derivation = derive_relationships(
            entities=entities,
            logical_adrs=logical_adrs,
            standalone_invariants=standalone_invariants,
            physical_adrs=physical_adrs,
            system_ids=system_ids,
            relationship_id=relationship_id,
        )
        relationships.update({item.relationship_id: item for item in relationship_derivation.relationships})
        for item in relationship_derivation.relationships:
            summary_list = getattr(entities[item.from_entity_id].relationships, item.relationship_type)
            if item.to_entity_id not in summary_list:
                summary_list.append(item.to_entity_id)
                summary_list.sort()

        unresolved_detection = detect_unresolved(
            relationship_derivation.generator_gaps,
            provenance=provenance,
        )
        unresolved.extend(unresolved_detection.unresolved)

        return FixedOrderPassRunResult(
            logical_extraction=logical_extraction,
            invariant_resolution=invariant_resolution,
            physical_extraction=physical_extraction,
            relationship_derivation=relationship_derivation,
            unresolved_detection=unresolved_detection,
        )

    def validate(
        self,
        entity_registry: NormalizedEntityRegistry,
        relationship_registry: RelationshipRegistry,
        unresolved_registry: UnresolvedRegistry,
        *,
        diagnostics=None,
    ) -> BundleValidationResult:
        """Run the extracted bundle validation step as the final fixed-order check."""

        return validate_bundle(
            entity_registry,
            relationship_registry,
            unresolved_registry,
            diagnostics=diagnostics,
        )
