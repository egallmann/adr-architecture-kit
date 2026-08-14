from __future__ import annotations

import pytest

from adr_kit.decorators import (
    enforces_invariant,
    enforces_invariants,
    enforces_uuids,
    implements,
    implements_adr,
    implements_adrs,
    implements_uuids,
    embodies,
)

SAMPLE_UUID = "019fee89-e615-7577-8d37-dd0df031bec9"
INVARIANT_UUID = "019fee89-e615-7129-ac3e-8120e0d7c106"


def test_implements_adr_attaches_ordered_metadata_to_function() -> None:
    @implements_adr("ADR-L-0001", "ADR-L-0013")
    def sample() -> str:
        return "ok"

    assert sample() == "ok"
    assert sample.__implements_adrs__ == ("ADR-L-0001", "ADR-L-0013")


def test_implements_adrs_accepts_sequence_literal_style() -> None:
    @implements_adrs(["ADR-L-0001", "ADR-L-0013"])
    def sample() -> str:
        return "ok"

    assert sample() == "ok"
    assert sample.__implements_adrs__ == ("ADR-L-0001", "ADR-L-0013")


def test_enforces_invariant_attaches_ordered_metadata_to_class() -> None:
    @enforces_invariant("INV-8801")
    class Sample:
        def value(self) -> str:
            return "ok"

    assert Sample().__class__.__enforces_invariants__ == ("INV-8801",)
    assert Sample().value() == "ok"


def test_enforces_invariants_accepts_sequence_literal_style() -> None:
    @enforces_invariants(["INV-8801", "INV-8802"])
    def sample() -> int:
        return 1

    assert sample.__enforces_invariants__ == ("INV-8801", "INV-8802")


@pytest.mark.parametrize(
    ("factory", "args", "error_type"),
    [
        (implements_adr, (), ValueError),
        (implements_adr, ("ADR-L-0001", "ADR-L-0001"), ValueError),
        (implements_adr, ("ADR-L-0001", 7), TypeError),
        (implements_adrs, ("not-a-seq",), TypeError),
        (implements_adrs, ([],), ValueError),
        (enforces_invariant, (), ValueError),
        (enforces_invariant, ("INV-8801", " INV-8801 "), ValueError),
        (enforces_invariant, ("INV-8801", None), TypeError),
        (enforces_invariants, ("INV-8801",), TypeError),
        (enforces_invariants, ([],), ValueError),
    ],
)
def test_decorator_factories_reject_invalid_inputs(factory, args, error_type) -> None:
    with pytest.raises(error_type):
        factory(*args)


def test_legacy_last_write_wins_and_does_not_synthesize_uuid_claims() -> None:
    @implements_adr("ADR-L-0001")
    @implements_adr("ADR-L-0002")
    def sample() -> str:
        return "ok"

    assert sample() == "ok"
    assert sample.__implements_adrs__ == ("ADR-L-0001",)
    assert not hasattr(sample, "__architecture_attribution_claims__")


def test_uuid_decorators_compose_declared_claims_without_touching_legacy() -> None:
    @implements(SAMPLE_UUID)
    @implements_adr("ADR-L-0004")
    def sample() -> None:
        return None

    assert sample.__implements_adrs__ == ("ADR-L-0004",)
    assert sample.__architecture_attribution_claims__ == (
        {
            "relationship": "implements",
            "target_entity_id": SAMPLE_UUID,
            "confidence": "declared",
        },
    )


def test_uuid_sequence_forms_and_stacked_relationships() -> None:
    @implements_uuids([SAMPLE_UUID])
    @enforces_uuids([INVARIANT_UUID])
    @embodies("019fee89-e618-7d04-9337-4aa2d3258507")
    def sample() -> int:
        return 1

    assert sample() == 1
    relationships = [claim["relationship"] for claim in sample.__architecture_attribution_claims__]
    assert set(relationships) == {"implements", "enforces", "embodies"}
    assert all(
        claim["confidence"] == "declared" for claim in sample.__architecture_attribution_claims__
    )
    assert not hasattr(sample, "__implements_adrs__")
