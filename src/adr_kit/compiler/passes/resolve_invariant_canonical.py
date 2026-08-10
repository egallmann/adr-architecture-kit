"""Canonical invariant resolution pass helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
        invariant_mentions: dict[str, list[tuple[dict[str, Any], str, str]]],
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


def _is_standalone_definition(inv_id: str, source_ref: str) -> bool:
    return source_ref == inv_id


def _is_adr_definition(source_ref: str) -> bool:
    return "#" in source_ref and source_ref.startswith("ADR-")


def _statement_payload(mention: tuple[dict[str, Any], str, str]) -> str:
    payload = mention[0]
    metadata = payload.get("metadata") or {}
    statement = metadata.get("statement") if isinstance(metadata, dict) else None
    if statement is None:
        statement = payload.get("summary") or ""
    return statement if isinstance(statement, str) else str(statement)


def resolve_invariant_canonical(
    invariant_mentions: dict[str, list[tuple[dict[str, Any], str, str]]],
    *,
    canonical,
    provenance,
    complete,
) -> InvariantResolutionResult:
    """Resolve canonical invariants from ADR-L definitions; fail closed on Class A/B."""

    result = InvariantResolutionResult()

    for inv_id, mentions in invariant_mentions.items():
        definitions = [
            item
            for item in mentions
            if _is_adr_definition(item[2]) or _is_standalone_definition(inv_id, item[2])
        ]
        references = [item for item in mentions if item not in definitions]

        standalone_defs = [item for item in definitions if _is_standalone_definition(inv_id, item[2])]
        adr_defs = [item for item in definitions if _is_adr_definition(item[2])]

        if standalone_defs:
            # Standalone definition authority is retired; colliding with ADR-L is Class A/B.
            if adr_defs or len(standalone_defs) > 1:
                statements = [_statement_payload(item) for item in definitions]
                if len(set(statements)) == 1 and len(definitions) > 1:
                    raise ValueError(
                        f"DUPLICATE_DEFINITION_ERROR: multiple definitions for {inv_id}"
                    )
                raise ValueError(
                    f"SEMANTIC_COLLISION_ERROR: multiple definitions for {inv_id} "
                    f"with unequal statements (standalone invariant authority retired)"
                )
            raise ValueError(
                f"STANDALONE_INVARIANT_AUTHORITY_RETIRED: {inv_id} defined outside ADR-L"
            )

        if len(adr_defs) == 0:
            raise ValueError(f"No canonical ADR-L definition for invariant {inv_id}")

        if len(adr_defs) > 1:
            statements = [_statement_payload(item) for item in adr_defs]
            if len(set(statements)) == 1:
                raise ValueError(
                    f"DUPLICATE_DEFINITION_ERROR: multiple definitions for {inv_id}"
                )
            raise ValueError(
                f"SEMANTIC_COLLISION_ERROR: multiple definitions for {inv_id} "
                f"with unequal statements"
            )

        payload, artifact, source_ref = adr_defs[0]
        entity = NormalizedEntity(
            id=inv_id,
            entity_type="invariant",
            name=payload["name"],
            summary=payload["summary"],
            canonical_source=canonical("logical_adr", source_ref, artifact),
            metadata=payload["metadata"],
            completeness=complete(),
            provenance=provenance(
                "logical_adr",
                source_ref,
                "assign_canonical_invariant",
                "explicit",
            ),
        )

        refs: list[SourceRef] = []
        for _, ref_artifact, ref_source in references:
            refs.append(
                SourceRef(
                    source_type="logical_adr" if ref_source.startswith("ADR-") else "derived",
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
