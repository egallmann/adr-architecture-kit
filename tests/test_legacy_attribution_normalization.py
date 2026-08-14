"""Repository-aware 1.0/1.2 → 1.5 normalization is fail-closed and idempotent."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from adr_kit.models.implementation_attribution import (
    ImplementationAttributionEvidence,
    ImplementationAttributionProvenance,
    ImplementationAttributionRecord,
)
from adr_kit.semantic_attribution import (
    AttributionNormalizationError,
    evidence_to_canonical_dict,
    normalize_attribution_evidence,
)

ADR_UUID = "019fee89-e615-7577-8d37-dd0df031bec9"
INV_UUID = "019fee89-e615-7129-ac3e-8120e0d7c106"
CAP_UUID = "019fee89-e615-7dd6-b137-8546c4e74c22"


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
        self._by_alias: dict[str, list[StubEntity]] = {}
        for entity in entities:
            self._by_alias.setdefault(entity.alias_id, []).append(entity)

    def find_entity_by_uuid(self, uuid: str) -> StubEntity | None:
        return self._by_uuid.get(uuid)

    def find_entity_by_alias_id(self, alias_id: str) -> StubEntity | None:
        matches = self._by_alias.get(alias_id, [])
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(f"ambiguous alias {alias_id}")
        return matches[0]


def _lookup() -> StubLookup:
    return StubLookup(
        StubEntity(ADR_UUID, "adr", "ADR-L-0004"),
        StubEntity(INV_UUID, "invariant", "INV-0027"),
        StubEntity(CAP_UUID, "capability", "CAP-0021"),
    )


def _legacy_doc() -> ImplementationAttributionEvidence:
    return ImplementationAttributionEvidence(
        schema_version="1.2",
        records=[
            ImplementationAttributionRecord(
                implementation_entity_id="function.sample",
                implementation_entity_type="function",
                attributed_adrs=["ADR-L-0004"],
                enforced_invariants=["INV-0027"],
                attributed_capabilities=["CAP-0021"],
                provenance=ImplementationAttributionProvenance(
                    source_file="b.py",
                    extractor="test",
                    commit="bbbb",
                ),
            ),
            ImplementationAttributionRecord(
                implementation_entity_id="function.other",
                implementation_entity_type="function",
                attributed_adrs=[ADR_UUID],
                provenance=ImplementationAttributionProvenance(
                    source_file="a.py",
                    extractor="test",
                ),
            ),
        ],
    )


def test_legacy_aliases_and_uuids_normalize_to_v15_without_required_type() -> None:
    canonical = normalize_attribution_evidence(_legacy_doc(), _lookup())
    dumped = evidence_to_canonical_dict(canonical)
    assert dumped["schema_version"] == "1.5"
    claims = dumped["records"][0]["claims"]
    assert dumped["records"][0]["implementation_entity_id"] == "function.other"
    assert all("asserted_target_entity_type" not in claim for claim in claims)
    targets = {
        (claim["relationship"], claim["target_entity_id"])
        for record in dumped["records"]
        for claim in record["claims"]
    }
    assert ("implements", ADR_UUID) in targets
    assert ("enforces", INV_UUID) in targets
    assert ("implements", CAP_UUID) in targets


def test_normalize_is_idempotent() -> None:
    lookup = _lookup()
    first = normalize_attribution_evidence(_legacy_doc(), lookup)
    second = normalize_attribution_evidence(first, lookup)
    assert evidence_to_canonical_dict(first) == evidence_to_canonical_dict(second)


def test_unresolved_alias_fails_closed() -> None:
    doc = ImplementationAttributionEvidence(
        records=[
            ImplementationAttributionRecord(
                implementation_entity_id="function.sample",
                implementation_entity_type="function",
                attributed_adrs=["ADR-L-9999"],
                provenance=ImplementationAttributionProvenance(
                    source_file="a.py",
                    extractor="test",
                ),
            )
        ]
    )
    with pytest.raises(AttributionNormalizationError, match="unresolved alias"):
        normalize_attribution_evidence(doc, _lookup())


def test_ambiguous_alias_fails_closed() -> None:
    lookup = StubLookup(
        StubEntity(ADR_UUID, "adr", "ADR-L-0004"),
        StubEntity("019ffdba-3c42-7c4a-a737-f6751a265d60", "adr", "ADR-L-0004"),
    )
    doc = ImplementationAttributionEvidence(
        records=[
            ImplementationAttributionRecord(
                implementation_entity_id="function.sample",
                implementation_entity_type="function",
                attributed_adrs=["ADR-L-0004"],
                provenance=ImplementationAttributionProvenance(
                    source_file="a.py",
                    extractor="test",
                ),
            )
        ]
    )
    with pytest.raises(AttributionNormalizationError, match="ambiguous alias"):
        normalize_attribution_evidence(doc, lookup)
