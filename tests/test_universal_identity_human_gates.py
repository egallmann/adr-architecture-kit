from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "adrs" / "logical" / "ADR-L-0022-universal-uuidv7-entity-identity.yaml"
UNIVERSAL_MAP = ROOT / "adrs" / "migrations" / "universal-uuidv7-allocation.yaml"
V13_MAP = ROOT / "adrs" / "migrations" / "canonical-identity-v13-map.yaml"


def _adr() -> dict[str, object]:
    return yaml.safe_load(ADR.read_text(encoding="utf-8"))


def test_human_gates_remain_explicitly_unapproved_in_durable_authority() -> None:
    document = _adr()
    decisions = {item["alias_id"]: item for item in document["decisions"]}
    invariants = {item["alias_id"]: item for item in document["invariants"]}

    assert "DEC-0145" in decisions
    assert "DEC-0146" in decisions
    assert "INV-0140" in invariants
    gate_text = "\n".join(
        str(decisions[key].get("rationale", "")) for key in ("DEC-0145", "DEC-0146")
    )
    assert "collision" in gate_text
    assert "human approval" in gate_text
    assert "SEALED" in gate_text


def test_universal_map_is_not_created_or_authoritative_before_human_approval() -> None:
    assert not UNIVERSAL_MAP.exists()
    existing_map = yaml.safe_load(V13_MAP.read_text(encoding="utf-8"))
    assert existing_map["type"] == "canonical_identity_v13_map"
    assert existing_map["seal"]["sealed"] is True


def test_relationship_deduplication_guard_is_durable_and_runtime_unchanged() -> None:
    source = (
        ROOT / "src" / "adr_kit" / "compiler" / "passes" / "derive_relationships.py"
    ).read_text(encoding="utf-8")
    document = _adr()
    text = "\n".join(
        str(item.get(field, ""))
        for item in document["decisions"]
        for field in ("summary", "rationale")
    )

    assert "relationships: dict[str, DerivedRelationship]" in source
    assert "if rel_id in relationships:" in source
    assert "multiple assertions" in text
    assert "inverse" in text
