"""R11 — semantic parity after identity migration."""

from __future__ import annotations

from adr_kit.migrators.identity_v13 import compare_semantic_parity


def test_relationship_multiset_parity_after_inverse_substitution() -> None:
    before = [
        ("declared_in", "CAP-9001", "ADR-L-9001"),
        ("enforces", "INV-9001", "CAP-9001"),
        ("enforces", "INV-9001", "CAP-9001"),
    ]
    after = [
        ("declared_in", "uuid-cap", "uuid-adr"),
        ("enforces", "uuid-inv", "uuid-cap"),
        ("enforces", "uuid-inv", "uuid-cap"),
    ]
    mapping = {
        "uuid-cap": "CAP-9001",
        "uuid-adr": "ADR-L-9001",
        "uuid-inv": "INV-9001",
    }
    assert (
        compare_semantic_parity(
            before_relationships=before,
            after_relationships=after,
            uuid_to_legacy=mapping,
        )
        == []
    )


def test_relationship_parity_detects_retargeting() -> None:
    before = [("declared_in", "CAP-9001", "ADR-L-9001")]
    after = [("declared_in", "uuid-cap", "uuid-other")]
    mapping = {"uuid-cap": "CAP-9001", "uuid-other": "ADR-L-9999"}
    errors = compare_semantic_parity(
        before_relationships=before,
        after_relationships=after,
        uuid_to_legacy=mapping,
    )
    assert errors
    assert "mismatch" in errors[0]


def test_count_equality_is_insufficient_for_parity() -> None:
    before = [
        ("declared_in", "CAP-9001", "ADR-L-9001"),
        ("enforces", "INV-9001", "CAP-9001"),
    ]
    after = [
        ("declared_in", "uuid-cap", "uuid-adr"),
        ("related_to", "uuid-inv", "uuid-cap"),
    ]
    mapping = {
        "uuid-cap": "CAP-9001",
        "uuid-adr": "ADR-L-9001",
        "uuid-inv": "INV-9001",
    }
    errors = compare_semantic_parity(
        before_relationships=before,
        after_relationships=after,
        uuid_to_legacy=mapping,
    )
    assert errors
