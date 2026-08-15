"""Resolved-type matrix and optional asserted-type checks for v1.5 evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

from adr_kit.models.implementation_attribution import (
    ImplementationAttributionEvidenceV15,
    ImplementationAttributionProvenance,
    ImplementationAttributionRecordV15,
    SemanticAttributionClaim,
)
from adr_kit.schema.implementation_attribution_validation import (
    validate_implementation_attribution_evidence,
)

DECISION_UUID = "019ffdba-3c42-700c-ac3f-8135e0139dfb"
INVARIANT_UUID = "019ffdba-3c42-7cbe-a121-06d3437129ed"
SYSTEM_UUID = "019fee89-e618-7d04-9337-4aa2d3258507"
MISSING_UUID = "019ffdba-3c42-7ac2-8e2e-4c2ca6bb969e"


@dataclass
class StubEntity:
    id: str
    entity_type: str
    alias_id: str
    lifecycle_stage: str = "active"
    metadata: dict[str, str] = field(default_factory=dict)


class StubLookup:
    def __init__(self, *entities: StubEntity) -> None:
        self._by_uuid = {entity.id: entity for entity in entities}
        self._by_alias = {entity.alias_id: entity for entity in entities}

    def find_entity_by_uuid(self, uuid: str) -> StubEntity | None:
        return self._by_uuid.get(uuid)

    def find_entity_by_alias_id(self, alias_id: str) -> StubEntity | None:
        return self._by_alias.get(alias_id)


def _evidence(*claims: SemanticAttributionClaim) -> ImplementationAttributionEvidenceV15:
    return ImplementationAttributionEvidenceV15(
        records=[
            ImplementationAttributionRecordV15(
                implementation_entity_id="function.sample",
                implementation_entity_type="function",
                provenance=ImplementationAttributionProvenance(
                    source_file="src/sample.py",
                    extractor="test",
                ),
                claims=list(claims),
            )
        ]
    )


def test_raw_v15_claim_omits_target_type() -> None:
    claim = SemanticAttributionClaim(
        relationship="implements",
        target_entity_id=DECISION_UUID,
        confidence="declared",
    )
    dumped = claim.model_dump(exclude_none=True)
    assert "asserted_target_entity_type" not in dumped
    assert dumped["target_entity_id"] == DECISION_UUID


def test_implements_decision_is_admitted() -> None:
    lookup = StubLookup(StubEntity(DECISION_UUID, "decision", "DEC-0116"))
    result = validate_implementation_attribution_evidence(
        lookup,
        _evidence(
            SemanticAttributionClaim(
                relationship="implements",
                target_entity_id=DECISION_UUID,
                confidence="declared",
            )
        ),
    )
    assert result.is_valid


def test_enforces_non_invariant_fails() -> None:
    lookup = StubLookup(StubEntity(DECISION_UUID, "decision", "DEC-0116"))
    result = validate_implementation_attribution_evidence(
        lookup,
        _evidence(
            SemanticAttributionClaim(
                relationship="enforces",
                target_entity_id=DECISION_UUID,
                confidence="declared",
            )
        ),
    )
    assert result.is_valid is False
    assert "does not admit" in result.issues[0].message


def test_embodies_system_is_admitted() -> None:
    lookup = StubLookup(StubEntity(SYSTEM_UUID, "system", "ADR-PS-0002"))
    result = validate_implementation_attribution_evidence(
        lookup,
        _evidence(
            SemanticAttributionClaim(
                relationship="embodies",
                target_entity_id=SYSTEM_UUID,
                confidence="declared",
            )
        ),
    )
    assert result.is_valid


def test_unresolved_uuid_fails_closed() -> None:
    lookup = StubLookup(StubEntity(DECISION_UUID, "decision", "DEC-0116"))
    result = validate_implementation_attribution_evidence(
        lookup,
        _evidence(
            SemanticAttributionClaim(
                relationship="implements",
                target_entity_id=MISSING_UUID,
                confidence="declared",
            )
        ),
    )
    assert result.is_valid is False
    assert "does not exist" in result.issues[0].message


def test_asserted_type_mismatch_fails() -> None:
    lookup = StubLookup(StubEntity(DECISION_UUID, "decision", "DEC-0116"))
    result = validate_implementation_attribution_evidence(
        lookup,
        _evidence(
            SemanticAttributionClaim(
                relationship="implements",
                target_entity_id=DECISION_UUID,
                confidence="declared",
                asserted_target_entity_type="capability",
            )
        ),
    )
    assert result.is_valid is False
    assert "does not match resolved type" in result.issues[0].message


def test_mapping_context_is_insufficient_for_v15() -> None:
    result = validate_implementation_attribution_evidence(
        {"ADR-L-0004": "accepted"},
        _evidence(
            SemanticAttributionClaim(
                relationship="implements",
                target_entity_id=DECISION_UUID,
                confidence="declared",
            )
        ),
    )
    assert result.is_valid is False
    assert "UUID lookup" in result.issues[0].message


def test_superseded_target_is_a_warning() -> None:
    lookup = StubLookup(
        StubEntity(
            INVARIANT_UUID,
            "invariant",
            "INV-0103",
            lifecycle_stage="superseded",
        )
    )
    result = validate_implementation_attribution_evidence(
        lookup,
        _evidence(
            SemanticAttributionClaim(
                relationship="enforces",
                target_entity_id=INVARIANT_UUID,
                confidence="declared",
            )
        ),
    )
    assert result.is_valid
    assert result.warning_count == 1
