"""Phase 2 RED/GREEN contracts for assertion identity and binding projection."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from adr_kit.generators import ArchitectureIndexGenerator
from adr_kit.identity import derive_assertion_id
from adr_kit.models import RelationshipRecord
from adr_kit.scope import ProjectScopeResolver

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "v1_2" / "logical-bindings.yaml"


def _scope(root: Path, *, logical_payload: dict | None = None):
    shutil.copy2(ROOT / "PROJECT.yaml", root / "PROJECT.yaml")
    destination = root / "adrs" / "logical" / "ADR-L-9801-bindings.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if logical_payload is None:
        shutil.copy2(FIXTURE, destination)
    else:
        destination.write_text(yaml.safe_dump(logical_payload, sort_keys=False), encoding="utf-8")
    resolver = ProjectScopeResolver(explicit_scope=root)
    return resolver.resolve(), ArchitectureIndexGenerator(scope_resolver=resolver)


def test_assertion_identity_matches_locked_canonical_vector() -> None:
    assertion_id = derive_assertion_id(
        "binds_rule",
        "ADR-L-9801",
        "ste-rules:RULE-0001",
        "ADR-L-9801",
        "/rule_bindings/0",
    )

    assert assertion_id == ("asrt-589e60c8d3f8aa7b6434d833cecf7590888794a13c37d28bd20df005ad6503e1")


def test_assertion_identity_is_source_sensitive_and_order_independent() -> None:
    first = derive_assertion_id("related_to", "A", "B", "ADR-L-0001", None)
    second = derive_assertion_id("related_to", "A", "B", "ADR-L-0002", None)
    repeated = derive_assertion_id("related_to", "A", "B", "ADR-L-0001", None)

    assert first != second
    assert first == repeated


def test_relationship_record_round_trips_additive_assertion_fields() -> None:
    relationship = RelationshipRecord(
        relationship_id="related_to:A:B",
        assertion_id=derive_assertion_id("related_to", "A", "B", "ADR-L-0001", "/decisions/0"),
        relationship_type="related_to",
        from_entity_id="A",
        to_entity_id="B",
        provenance_classification="explicit",
        canonical_source_ref="ADR-L-0001",
        source_pointer="/decisions/0",
    )

    assert RelationshipRecord.model_validate(relationship.model_dump(mode="json")) == relationship


def test_binding_families_project_without_materializing_external_entities(
    tmp_path: Path,
) -> None:
    scope, generator = _scope(tmp_path)
    bundle = generator.generate_from_scope(scope)
    relationships = {
        (item.relationship_type, item.to_entity_id): item
        for item in bundle.relationship_registry.relationships
    }

    substrate = relationships[("binds_substrate", "ste-substrate:SUBSTRATE-0001")]
    rule = relationships[("binds_rule", "ste-rules:RULE-0001")]
    expectation = relationships[("expects_evidence", "EVID-9801")]
    assert substrate.from_entity_id == "ADR-L-9801"
    assert substrate.source_pointer == "/substrate_bindings/0"
    assert rule.metadata["disposition"] == "refined"
    assert rule.metadata["affected_entities"][1]["qualified_id"] == (
        "provider-architecture:CAP-0042"
    )
    assert expectation.metadata["observed_evidence"] is False
    assert all(item.assertion_id.startswith("asrt-") for item in relationships.values())

    entity_ids = {item.id for item in bundle.entity_registry.entities}
    assert "ste-substrate:SUBSTRATE-0001" not in entity_ids
    assert "ste-rules:RULE-0001" not in entity_ids
    assert "EVID-9801" not in entity_ids


def test_binding_projection_fails_for_unresolved_local_reference(tmp_path: Path) -> None:
    payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    payload["rule_bindings"][0]["affected_entities"][0] = "MISSING-ENTITY"
    scope, generator = _scope(tmp_path, logical_payload=payload)

    try:
        generator.generate_from_scope(scope)
    except ValueError as exc:
        assert "Unresolved local binding reference" in str(exc)
        assert "MISSING-ENTITY" in str(exc)
    else:
        raise AssertionError("unresolved local affected_entities reference must fail")


def test_binding_projection_is_deterministic(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first_scope, first_generator = _scope(first_root)
    second_scope, second_generator = _scope(second_root)

    first = first_generator.generate_from_scope(first_scope)
    second = second_generator.generate_from_scope(second_scope)

    assert first.relationship_registry.model_dump(mode="json") == (
        second.relationship_registry.model_dump(mode="json")
    )
