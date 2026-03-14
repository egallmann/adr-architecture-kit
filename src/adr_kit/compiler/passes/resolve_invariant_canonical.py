"""Canonical invariant resolution pass helper."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...models import NormalizedEntity, SourceRef
from .extract_logical_entities import ExtractedEntity


@dataclass(frozen=True)
class CanonicalInvariantSelection:
    """Canonical invariant entity plus reference mentions."""

    entity: NormalizedEntity
    reference_source_refs: list[SourceRef] = field(default_factory=list)


@dataclass
class InvariantResolutionResult:
    """Canonical invariant resolution output."""

    entities: list[ExtractedEntity] = field(default_factory=list)
    selections: dict[str, CanonicalInvariantSelection] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolveInvariantCanonicalPass:
    """Pass-shaped helper for canonical invariant selection."""

    name = "resolve_invariant_canonical"
    required = True
    depends_on: tuple[str, ...] = ()
    halts_on_error = True

    def run(
        self,
        invariant_mentions: dict[str, list[tuple[dict, str, str]]],
        *,
        canonical,
        provenance,
        complete,
    ) -> InvariantResolutionResult:
        return resolve_invariant_canonical(
            invariant_mentions,
            canonical=canonical,
            provenance=provenance,
            complete=complete,
        )


def resolve_invariant_canonical(
    invariant_mentions: dict[str, list[tuple[dict, str, str]]],
    *,
    canonical,
    provenance,
    complete,
) -> InvariantResolutionResult:
    """Resolve canonical invariants from mention sets using current generator rules."""

    result = InvariantResolutionResult()

    for inv_id, mentions in invariant_mentions.items():
        standalone = [item for item in mentions if item[2] == inv_id]
        local = [item for item in mentions if item[2] != inv_id]
        if len(standalone) > 1 or (not standalone and len(local) > 1):
            raise ValueError(f"Duplicate canonical invariant ID {inv_id}")

        payload, artifact, source_ref = standalone[0] if standalone else local[0]
        entity = NormalizedEntity(
            id=inv_id,
            entity_type="invariant",
            name=payload["name"],
            summary=payload["summary"],
            canonical_source=canonical("standalone_invariant" if standalone else "logical_adr", source_ref, artifact),
            metadata=payload["metadata"],
            completeness=complete(),
            provenance=provenance(
                "standalone_invariant" if standalone else "logical_adr",
                source_ref,
                "assign_canonical_invariant",
                "explicit",
            ),
        )

        refs: list[SourceRef] = []
        for _, ref_artifact, ref_source in mentions:
            if ref_source == source_ref and ref_artifact == artifact:
                continue
            refs.append(
                SourceRef(
                    source_type="logical_adr" if ref_source.startswith("ADR-") else "standalone_invariant",
                    source_ref=ref_source,
                    artifact_path=ref_artifact,
                    mention_role="reference",
                )
            )
        refs.sort(key=lambda item: (item.source_ref, item.mention_role))

        result.entities.append(ExtractedEntity(entity=entity))
        result.selections[inv_id] = CanonicalInvariantSelection(
            entity=entity,
            reference_source_refs=refs,
        )

    return result
