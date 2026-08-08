from __future__ import annotations

import pytest

from adr_kit.decorators import (
    enforces_invariant,
    enforces_invariants,
    implements_adr,
    implements_adrs,
)


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
    @enforces_invariant("INV-0006")
    class Sample:
        def value(self) -> str:
            return "ok"

    assert Sample().__class__.__enforces_invariants__ == ("INV-0006",)
    assert Sample().value() == "ok"


def test_enforces_invariants_accepts_sequence_literal_style() -> None:
    @enforces_invariants(["INV-0006", "INV-0007"])
    def sample() -> int:
        return 1

    assert sample.__enforces_invariants__ == ("INV-0006", "INV-0007")


@pytest.mark.parametrize(
    ("factory", "args", "error_type"),
    [
        (implements_adr, (), ValueError),
        (implements_adr, ("ADR-L-0001", "ADR-L-0001"), ValueError),
        (implements_adr, ("ADR-L-0001", 7), TypeError),
        (implements_adrs, ("not-a-seq",), TypeError),
        (implements_adrs, ([],), ValueError),
        (enforces_invariant, (), ValueError),
        (enforces_invariant, ("INV-0006", " INV-0006 "), ValueError),
        (enforces_invariant, ("INV-0006", None), TypeError),
        (enforces_invariants, ("INV-0006",), TypeError),
        (enforces_invariants, ([],), ValueError),
    ],
)
def test_decorator_factories_reject_invalid_inputs(factory, args, error_type) -> None:
    with pytest.raises(error_type):
        factory(*args)
