"""Canonical ordering, duplicate detection, and 1.0/1.2 → 1.5 normalization."""

from __future__ import annotations

from typing import Any, Protocol

from adr_kit.identity import UUIDV7_PATTERN, validate_uuidv7
from adr_kit.models.implementation_attribution import (
    AttributionEvidenceDocument,
    ImplementationAttributionEvidence,
    ImplementationAttributionEvidenceV15,
    ImplementationAttributionProvenance,
    ImplementationAttributionRecordV15,
    SemanticAttributionClaim,
    SemanticAttributionRelationship,
)
from adr_kit.semantic_attribution.vocabulary import RELATIONSHIP_ORDER


class AttributionLookup(Protocol):
    def find_entity_by_uuid(self, uuid: str) -> Any | None: ...

    def find_entity_by_alias_id(self, alias_id: str) -> Any | None: ...


class AttributionNormalizationError(ValueError):
    """Legacy or v1.5 evidence cannot be normalized fail-closed."""


def claim_sort_key(claim: SemanticAttributionClaim) -> tuple[str, str, str]:
    asserted = claim.asserted_target_entity_type or ""
    return (claim.relationship, claim.target_entity_id, asserted)


def record_sort_key(record: ImplementationAttributionRecordV15) -> tuple[str, str, str, str]:
    commit = record.provenance.commit or ""
    return (
        record.implementation_entity_id,
        record.provenance.source_file,
        record.provenance.extractor,
        commit,
    )


def provenance_key(record: ImplementationAttributionRecordV15) -> tuple[str, str, str]:
    return (
        record.provenance.source_file,
        record.provenance.extractor,
        record.provenance.commit or "",
    )


def sort_evidence(
    evidence: ImplementationAttributionEvidenceV15,
) -> ImplementationAttributionEvidenceV15:
    """Return a new document with canonical record and claim order."""

    sorted_records: list[ImplementationAttributionRecordV15] = []
    for record in sorted(evidence.records, key=record_sort_key):
        sorted_records.append(
            record.model_copy(update={"claims": sorted(record.claims, key=claim_sort_key)})
        )
    return evidence.model_copy(update={"records": sorted_records})


def collect_duplicate_errors(evidence: ImplementationAttributionEvidenceV15) -> list[str]:
    """Return fail-closed duplicate diagnostics; empty means structurally unique."""

    errors: list[str] = []
    seen_provenance: dict[tuple[str, str, str, str, str, str], str] = {}
    for record_index, record in enumerate(evidence.records):
        seen_in_record: set[tuple[str, str]] = set()
        for claim_index, claim in enumerate(record.claims):
            pair = (claim.relationship, claim.target_entity_id)
            if pair in seen_in_record:
                errors.append(
                    f"records[{record_index}].claims[{claim_index}]: duplicate "
                    f"({claim.relationship}, {claim.target_entity_id}) within one record"
                )
            seen_in_record.add(pair)
            identity = (
                record.implementation_entity_id,
                claim.relationship,
                claim.target_entity_id,
                *provenance_key(record),
            )
            previous = seen_provenance.get(identity)
            path = f"records[{record_index}].claims[{claim_index}]"
            if previous is not None:
                errors.append(
                    f"{path}: identical semantic triple and provenance already declared at {previous}"
                )
            else:
                seen_provenance[identity] = path
    return errors


def _relationship_for_legacy_field(field: str) -> SemanticAttributionRelationship:
    if field == "enforced_invariants":
        return "enforces"
    return "implements"


def _resolve_legacy_target(lookup: AttributionLookup, token: str, *, path: str) -> str:
    if UUIDV7_PATTERN.match(token):
        entity = lookup.find_entity_by_uuid(validate_uuidv7(token))
        if entity is None:
            raise AttributionNormalizationError(f"{path}: unresolved UUID {token}")
        return str(entity.id)
    try:
        entity = lookup.find_entity_by_alias_id(token)
    except Exception as exc:
        raise AttributionNormalizationError(f"{path}: ambiguous alias {token}") from exc
    if entity is None:
        raise AttributionNormalizationError(f"{path}: unresolved alias {token}")
    return str(entity.id)


def normalize_attribution_evidence(
    doc: AttributionEvidenceDocument | dict[str, Any],
    lookup: AttributionLookup,
) -> ImplementationAttributionEvidenceV15:
    """Translate 1.0/1.2 or sort 1.5 into canonical v1.5 evidence.

    Requires architecture lookup. Unresolved or ambiguous aliases fail closed.
    """

    if isinstance(doc, dict):
        version = doc.get("schema_version")
        if version == "1.5":
            parsed: AttributionEvidenceDocument = (
                ImplementationAttributionEvidenceV15.model_validate(doc)
            )
        elif version in ("1.0", "1.2", None):
            parsed = ImplementationAttributionEvidence.model_validate(doc)
        else:
            raise AttributionNormalizationError(f"unsupported evidence schema_version: {version!r}")
    else:
        parsed = doc

    if isinstance(parsed, ImplementationAttributionEvidenceV15):
        canonical = sort_evidence(parsed)
        errors = collect_duplicate_errors(canonical)
        if errors:
            raise AttributionNormalizationError("; ".join(errors))
        return canonical

    records: list[ImplementationAttributionRecordV15] = []
    for record_index, record in enumerate(parsed.records):
        claims: list[SemanticAttributionClaim] = []
        field_items = (
            ("attributed_adrs", record.attributed_adrs),
            ("enforced_invariants", record.enforced_invariants),
            ("attributed_capabilities", record.attributed_capabilities),
        )
        for field, tokens in field_items:
            relationship = _relationship_for_legacy_field(field)
            for token_index, token in enumerate(tokens):
                path = f"records[{record_index}].{field}[{token_index}]"
                target = _resolve_legacy_target(lookup, token, path=path)
                claims.append(
                    SemanticAttributionClaim(
                        relationship=relationship,
                        target_entity_id=target,
                        confidence=record.confidence,
                    )
                )
        records.append(
            ImplementationAttributionRecordV15(
                implementation_entity_id=record.implementation_entity_id,
                implementation_entity_type=record.implementation_entity_type,
                provenance=ImplementationAttributionProvenance(
                    source_file=record.provenance.source_file,
                    extractor=record.provenance.extractor,
                    commit=record.provenance.commit,
                ),
                claims=claims,
                metadata=dict(record.metadata),
                attribution_source_language=record.attribution_source_language,
            )
        )

    canonical = sort_evidence(
        ImplementationAttributionEvidenceV15(schema_version="1.5", records=records)
    )
    errors = collect_duplicate_errors(canonical)
    if errors:
        raise AttributionNormalizationError("; ".join(errors))
    return canonical


def evidence_to_canonical_dict(evidence: ImplementationAttributionEvidenceV15) -> dict[str, Any]:
    """Serialize canonical v1.5 evidence with stable field order."""

    canonical = sort_evidence(evidence)
    records: list[dict[str, Any]] = []
    for record in canonical.records:
        provenance: dict[str, Any] = {
            "source_file": record.provenance.source_file,
            "extractor": record.provenance.extractor,
        }
        if record.provenance.commit is not None:
            provenance["commit"] = record.provenance.commit
        payload: dict[str, Any] = {
            "implementation_entity_id": record.implementation_entity_id,
            "implementation_entity_type": record.implementation_entity_type,
            "provenance": provenance,
            "claims": [
                {
                    "relationship": claim.relationship,
                    "target_entity_id": claim.target_entity_id,
                    "confidence": claim.confidence,
                    **(
                        {"asserted_target_entity_type": claim.asserted_target_entity_type}
                        if claim.asserted_target_entity_type is not None
                        else {}
                    ),
                }
                for claim in record.claims
            ],
        }
        if record.metadata:
            payload["metadata"] = record.metadata
        if record.attribution_source_language is not None:
            payload["attribution_source_language"] = record.attribution_source_language
        records.append(payload)
    return {
        "schema_version": "1.5",
        "type": "implementation_attribution_evidence",
        "records": records,
    }


def unique_semantic_edges(
    evidence: ImplementationAttributionEvidenceV15,
) -> set[tuple[str, str, str]]:
    """Unique (implementation_entity_id, relationship, target_entity_id) triples."""

    return {
        (record.implementation_entity_id, claim.relationship, claim.target_entity_id)
        for record in evidence.records
        for claim in record.claims
    }


def relationship_occurrence_counts(
    evidence: ImplementationAttributionEvidenceV15,
) -> dict[str, int]:
    counts = {name: 0 for name in RELATIONSHIP_ORDER}
    for record in evidence.records:
        for claim in record.claims:
            counts[claim.relationship] = counts.get(claim.relationship, 0) + 1
    return counts
