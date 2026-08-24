from __future__ import annotations

from adr_kit.semantic_attribution.vocabulary import (
    allowed_target_entity_types,
    load_semantic_attribution_vocabulary,
)


def test_attribution_vocabulary_is_selected_by_evidence_version() -> None:
    assert load_semantic_attribution_vocabulary("1.5")["schema_version"] == "1.5"
    assert load_semantic_attribution_vocabulary("1.6")["schema_version"] == "1.6"
    assert allowed_target_entity_types("enforces", version="1.5") == frozenset({"invariant"})
    assert allowed_target_entity_types("enforces", version="1.6") == frozenset({"invariant"})
