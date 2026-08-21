"""Canonical ordering, duplicate detection, and lossless attribution normalization."""

from __future__ import annotations

from typing import Any, Protocol

from adr_kit.identity import UUIDV7_PATTERN, validate_uuidv7
from adr_kit.models.implementation_attribution import (
    AttributionEvidenceDocument,
    ImplementationAttributionEvidence,
    ImplementationAttributionEvidenceV15,
    ImplementationAttributionEvidenceV16,
    ImplementationAttributionProvenance,
    ImplementationAttributionProvenanceV16,
    ImplementationAttributionRecordV15,
    ImplementationAttributionRecordV16,
    SemanticAttributionClaim,
    SemanticAttributionRelationship,
)
from adr_kit.semantic_attribution.vocabulary import RELATIONSHIP_ORDER


class AttributionLookup(Protocol):
    def find_entity_by_uuid(self, uuid: str) -> Any | None: ...

    def find_entity_by_alias_id(self, alias_id: str) -> Any | None: ...


class AttributionNormalizationError(ValueError):
    """Evidence cannot be normalized to the requested target without semantic loss."""


SemanticAttributionRecord = ImplementationAttributionRecordV15 | ImplementationAttributionRecordV16


def semantic_records(
    evidence: ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16,
) -> list[SemanticAttributionRecord]:
    """Return version-narrowed records without collapsing their type to BaseModel."""

    if isinstance(evidence, ImplementationAttributionEvidenceV16):
        return list(evidence.records)
    return list(evidence.records)


def claim_sort_key(claim: SemanticAttributionClaim) -> tuple[str, str, str]:
    asserted = claim.asserted_target_entity_type or ""
    return (claim.relationship, claim.target_entity_id, asserted)


def record_sort_key(
    record: ImplementationAttributionRecordV15 | ImplementationAttributionRecordV16,
) -> tuple[str, str, str, int, int, str, str]:
    commit = record.provenance.commit or ""
    return (
        record.implementation_entity_id,
        record.provenance.source_file,
        getattr(record.provenance, "source_pointer", None) or "",
        getattr(record.provenance, "start_line", None) or 0,
        getattr(record.provenance, "end_line", None) or 0,
        record.provenance.extractor,
        commit,
    )


def provenance_key(
    record: ImplementationAttributionRecordV15 | ImplementationAttributionRecordV16,
) -> tuple[str, str, int, int, str, str]:
    return (
        record.provenance.source_file,
        getattr(record.provenance, "source_pointer", None) or "",
        getattr(record.provenance, "start_line", None) or 0,
        getattr(record.provenance, "end_line", None) or 0,
        record.provenance.extractor,
        record.provenance.commit or "",
    )


def sort_evidence(
    evidence: ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16,
) -> ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16:
    """Return a new document with canonical record and claim order."""

    sorted_records: list[
        ImplementationAttributionRecordV15 | ImplementationAttributionRecordV16
    ] = []
    for record in sorted(semantic_records(evidence), key=record_sort_key):
        sorted_records.append(
            record.model_copy(update={"claims": sorted(record.claims, key=claim_sort_key)})
        )
    return evidence.model_copy(update={"records": sorted_records})


def collect_duplicate_errors(
    evidence: ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16,
) -> list[str]:
    """Return fail-closed duplicate diagnostics; empty means structurally unique."""

    errors: list[str] = []
    seen_provenance: dict[tuple[object, ...], str] = {}
    for record_index, record in enumerate(semantic_records(evidence)):
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
    *,
    target_version: str = "1.5",
) -> ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16:
    """Normalize supported evidence to an explicit lossless v1.5 or v1.6 target.

    Requires architecture lookup. Unresolved or ambiguous aliases fail closed.
    """

    if target_version not in {"1.5", "1.6"}:
        raise AttributionNormalizationError(
            f"unsupported target evidence version: {target_version!r}"
        )

    parsed: AttributionEvidenceDocument
    if isinstance(doc, dict):
        version = doc.get("schema_version")
        if version == "1.6":
            parsed = ImplementationAttributionEvidenceV16.model_validate(doc)
        elif version == "1.5":
            parsed = ImplementationAttributionEvidenceV15.model_validate(doc)
        elif version in ("1.0", "1.2", None):
            parsed = ImplementationAttributionEvidence.model_validate(doc)
        else:
            raise AttributionNormalizationError(f"unsupported evidence schema_version: {version!r}")
    else:
        parsed = doc

    if isinstance(parsed, ImplementationAttributionEvidenceV16):
        canonical_v16 = sort_evidence(parsed)
        assert isinstance(canonical_v16, ImplementationAttributionEvidenceV16)
        errors = collect_duplicate_errors(canonical_v16)
        if errors:
            raise AttributionNormalizationError("; ".join(errors))
        _validate_v16_confidence(canonical_v16)
        if target_version == "1.6":
            return canonical_v16
        for index, record in enumerate(canonical_v16.records):
            populated = [
                name
                for name in ("source_pointer", "start_line", "end_line")
                if getattr(record.provenance, name) is not None
            ]
            if populated:
                raise AttributionNormalizationError(
                    f"records[{index}]: lossy v1.6 to v1.5 conversion would discard "
                    + ", ".join(populated)
                )
        downgraded = ImplementationAttributionEvidenceV15(
            records=[
                ImplementationAttributionRecordV15(
                    implementation_entity_id=record.implementation_entity_id,
                    implementation_entity_type=record.implementation_entity_type,
                    provenance=ImplementationAttributionProvenance(
                        source_file=record.provenance.source_file,
                        extractor=record.provenance.extractor,
                        commit=record.provenance.commit,
                    ),
                    claims=[claim.model_copy(deep=True) for claim in record.claims],
                    metadata=dict(record.metadata),
                    attribution_source_language=record.attribution_source_language,
                )
                for record in canonical_v16.records
            ]
        )
        canonical_downgrade = sort_evidence(downgraded)
        assert isinstance(canonical_downgrade, ImplementationAttributionEvidenceV15)
        return canonical_downgrade

    if isinstance(parsed, ImplementationAttributionEvidenceV15):
        canonical = sort_evidence(parsed)
        assert isinstance(canonical, ImplementationAttributionEvidenceV15)
        errors = collect_duplicate_errors(canonical)
        if errors:
            raise AttributionNormalizationError("; ".join(errors))
        if target_version == "1.5":
            return canonical
        promoted = ImplementationAttributionEvidenceV16(
            records=[
                ImplementationAttributionRecordV16(
                    implementation_entity_id=record.implementation_entity_id,
                    implementation_entity_type=record.implementation_entity_type,
                    provenance=ImplementationAttributionProvenanceV16(
                        source_file=record.provenance.source_file,
                        extractor=record.provenance.extractor,
                        commit=record.provenance.commit,
                    ),
                    claims=[claim.model_copy(deep=True) for claim in record.claims],
                    metadata=dict(record.metadata),
                    attribution_source_language=record.attribution_source_language,
                )
                for record in canonical.records
            ]
        )
        _validate_v16_confidence(promoted)
        canonical_promotion = sort_evidence(promoted)
        assert isinstance(canonical_promotion, ImplementationAttributionEvidenceV16)
        return canonical_promotion

    records: list[ImplementationAttributionRecordV15] = []
    for record_index, legacy_record in enumerate(parsed.records):
        claims: list[SemanticAttributionClaim] = []
        field_items = (
            ("attributed_adrs", legacy_record.attributed_adrs),
            ("enforced_invariants", legacy_record.enforced_invariants),
            ("attributed_capabilities", legacy_record.attributed_capabilities),
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
                        confidence=legacy_record.confidence,
                    )
                )
        records.append(
            ImplementationAttributionRecordV15(
                implementation_entity_id=legacy_record.implementation_entity_id,
                implementation_entity_type=legacy_record.implementation_entity_type,
                provenance=ImplementationAttributionProvenance(
                    source_file=legacy_record.provenance.source_file,
                    extractor=legacy_record.provenance.extractor,
                    commit=legacy_record.provenance.commit,
                ),
                claims=claims,
                metadata=dict(legacy_record.metadata),
                attribution_source_language=legacy_record.attribution_source_language,
            )
        )

    canonical = sort_evidence(
        ImplementationAttributionEvidenceV15(schema_version="1.5", records=records)
    )
    assert isinstance(canonical, ImplementationAttributionEvidenceV15)
    errors = collect_duplicate_errors(canonical)
    if errors:
        raise AttributionNormalizationError("; ".join(errors))
    if target_version == "1.5":
        return canonical
    return normalize_attribution_evidence(canonical, lookup, target_version="1.6")


def _validate_v16_confidence(evidence: ImplementationAttributionEvidenceV16) -> None:
    for record_index, record in enumerate(evidence.records):
        for claim_index, claim in enumerate(record.claims):
            if claim.relationship == "enforces" and claim.confidence != "declared":
                raise AttributionNormalizationError(
                    f"v1.6 records[{record_index}].claims[{claim_index}]: "
                    "enforces requires confidence declared"
                )


def evidence_to_canonical_dict(
    evidence: ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16,
) -> dict[str, Any]:
    """Serialize canonical v1.5/v1.6 evidence with stable field order."""

    canonical = sort_evidence(evidence)
    records: list[dict[str, Any]] = []
    for record in semantic_records(canonical):
        provenance: dict[str, Any] = {
            "source_file": record.provenance.source_file,
            "extractor": record.provenance.extractor,
        }
        if record.provenance.commit is not None:
            provenance["commit"] = record.provenance.commit
        if isinstance(record, ImplementationAttributionRecordV16):
            if record.provenance.source_pointer is not None:
                provenance["source_pointer"] = record.provenance.source_pointer
            if record.provenance.start_line is not None:
                provenance["start_line"] = record.provenance.start_line
            if record.provenance.end_line is not None:
                provenance["end_line"] = record.provenance.end_line
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
        "schema_version": evidence.schema_version,
        "type": "implementation_attribution_evidence",
        "records": records,
    }


def unique_semantic_edges(
    evidence: ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16,
) -> set[tuple[str, str, str]]:
    """Unique (implementation_entity_id, relationship, target_entity_id) triples."""

    return {
        (record.implementation_entity_id, claim.relationship, claim.target_entity_id)
        for record in semantic_records(evidence)
        for claim in record.claims
    }


def relationship_occurrence_counts(
    evidence: ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16,
) -> dict[str, int]:
    counts = {name: 0 for name in RELATIONSHIP_ORDER}
    for record in semantic_records(evidence):
        for claim in record.claims:
            counts[claim.relationship] = counts.get(claim.relationship, 0) + 1
    return counts
