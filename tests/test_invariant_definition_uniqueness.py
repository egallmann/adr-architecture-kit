"""RED/GREEN: Class A/B invariant definition uniqueness (R3/R6)."""

from __future__ import annotations

import pytest

from adr_kit.compiler.passes.resolve_invariant_canonical import resolve_invariant_canonical
from adr_kit.generators.architecture_index_generator import ArchitectureIndexGenerator


def _mention(
    *,
    inv_id: str,
    adr_id: str,
    statement: str,
    artifact: str | None = None,
) -> tuple[dict, str, str]:
    return (
        {
            "name": inv_id,
            "summary": statement,
            "metadata": {
                "adr_id": adr_id,
                "scope": "global",
                "statement": statement,
                "enforcement_level": "must",
                "declaration_mode": "local",
                "upheld_by_decisions": [],
            },
        },
        artifact or f"adrs/logical/{adr_id}.yaml",
        f"{adr_id}#{inv_id}",
    )


def _resolve(mentions: dict):
    generator = ArchitectureIndexGenerator()
    return resolve_invariant_canonical(
        mentions,
        canonical=generator._canonical,
        provenance=generator._provenance,
        complete=generator._complete,
    )


def test_class_a_semantic_collision_unequal_statements():
    """Two definitions, different statements → SEMANTIC_COLLISION_ERROR."""
    mentions = {
        "INV-1000": [
            _mention(inv_id="INV-1000", adr_id="ADR-L-1000", statement="Statement alpha."),
            _mention(inv_id="INV-1000", adr_id="ADR-L-1001", statement="Statement beta."),
        ]
    }
    with pytest.raises(ValueError, match="SEMANTIC_COLLISION_ERROR"):
        _resolve(mentions)


def test_class_b_duplicate_definition_equal_statements():
    """Two definitions, identical statements → DUPLICATE_DEFINITION_ERROR."""
    stmt = "Exactly the same statement."
    mentions = {
        "INV-1000": [
            _mention(inv_id="INV-1000", adr_id="ADR-L-1000", statement=stmt),
            _mention(inv_id="INV-1000", adr_id="ADR-L-1001", statement=stmt),
        ]
    }
    with pytest.raises(ValueError, match="DUPLICATE_DEFINITION_ERROR"):
        _resolve(mentions)


def test_one_definition_many_references_valid():
    """One establishing definition remains valid (references are not definitions)."""
    mentions = {
        "INV-1000": [
            _mention(
                inv_id="INV-1000",
                adr_id="ADR-L-1000",
                statement="Single canonical definition.",
            )
        ]
    }
    result = _resolve(mentions)
    assert result.selections["INV-1000"].entity.canonical_source.source_type == "logical_adr"
    assert result.selections["INV-1000"].entity.canonical_source.source_ref == "ADR-L-1000#INV-1000"


def test_paraphrased_statements_are_semantic_collision():
    """Similar but not exactly equal statements → SEMANTIC_COLLISION_ERROR."""
    mentions = {
        "INV-1000": [
            _mention(
                inv_id="INV-1000",
                adr_id="ADR-L-1000",
                statement="Rendered artifacts are derived only.",
            ),
            _mention(
                inv_id="INV-1000",
                adr_id="ADR-L-1001",
                statement="Rendered artifacts must be derived-only.",
            ),
        ]
    }
    with pytest.raises(ValueError, match="SEMANTIC_COLLISION_ERROR"):
        _resolve(mentions)


def test_inv_0008_class_cannot_silently_prefer_standalone():
    """Historical INV-0008 class: ADR-L + standalone-shaped mention must not silently win."""
    inv_id = "INV-1008"
    adr_statement = (
        "Every admitted v1.3 entity's canonical machine identity is a lowercase RFC 9562 UUIDv7."
    )
    standalone_statement = "Rendered markdown artifacts are derived only."
    mentions = {
        inv_id: [
            _mention(inv_id=inv_id, adr_id="ADR-L-1019", statement=adr_statement),
            (
                {
                    "name": inv_id,
                    "summary": standalone_statement,
                    "metadata": {
                        "defined_in": "ADR-L-1014",
                        "scope": "global",
                        "statement": standalone_statement,
                        "enforcement_level": "must",
                        "declaration_mode": "canonical",
                        "upheld_by_decisions": [],
                        "enforced_by": [],
                    },
                },
                f"adrs/invariants/{inv_id}.yaml",
                inv_id,  # standalone source_ref shape
            ),
        ]
    }
    with pytest.raises(ValueError, match="SEMANTIC_COLLISION_ERROR|STANDALONE_INVARIANT|DUPLICATE"):
        _resolve(mentions)
