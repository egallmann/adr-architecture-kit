from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "docs" / "design-journal" / "2026-universal-uuidv7-entity-identity.md"
PACKET = ROOT / "docs" / "design-journal" / "2026-universal-uuidv7-human-gates.md"
COLLISIONS = (
    ROOT
    / "docs"
    / "design-journal"
    / "2026-universal-uuidv7-alias-collision-disposition.yaml"
)
UNIVERSAL_MAP = ROOT / "adrs" / "migrations" / "universal-uuidv7-allocation.yaml"
V13_MAP = ROOT / "adrs" / "migrations" / "canonical-identity-v13-map.yaml"


def test_human_packet_keeps_all_five_gates_explicitly_unapproved() -> None:
    text = PACKET.read_text(encoding="utf-8")

    for gate in (
        "ALIAS_COLLISIONS_APPROVED=NO",
        "VNEXT_CONTRACT_APPROVED=NO",
        "GRAPH_VNEXT_CONTRACT_APPROVED=NO",
        "ALLOCATION_MAP_CONTRACT_APPROVED=NO",
        "UUID_ALLOCATION_MAP_SEALED=NO",
        "UNIVERSAL_IDENTITY_MIGRATION_READY=NO",
    ):
        assert gate in text
    assert "VNEXT_CONTRACT_APPROVED: [ ] YES / [ ] NO" in text
    assert "GRAPH_VNEXT_CONTRACT_APPROVED: [ ] YES / [ ] NO" in text
    assert "ALLOCATION_MAP_CONTRACT_APPROVED: [ ] YES / [ ] NO" in text


def test_collision_candidates_are_unique_monotonic_and_unallocated() -> None:
    document = yaml.safe_load(COLLISIONS.read_text(encoding="utf-8"))
    candidate_validation = document["candidate_validation"]
    candidates = [
        candidate
        for item in document["collisions"]
        for candidate in item["proposed_replacements"]["candidates"]
    ]

    assert len(candidates) == len(set(candidates))
    assert candidate_validation["uniqueness_across_groups"] is True
    assert candidate_validation["monotonic_after_high_water_marks"] is True
    assert all(not item["candidate_collisions"] for item in candidate_validation["namespaces"].values())
    assert all(not item["reused_retired_aliases"] for item in candidate_validation["namespaces"].values())

    # Candidate values must not already be present in canonical or package
    # contract surfaces. Review prose and this test are intentionally excluded.
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for base in (ROOT / "adrs", ROOT / "schema", ROOT / "src")
        for path in base.rglob("*")
        if path.is_file()
    )
    assert all(candidate not in source_text for candidate in candidates)


def test_universal_map_is_not_created_or_authoritative_before_human_approval() -> None:
    assert not UNIVERSAL_MAP.exists()
    existing_map = yaml.safe_load(V13_MAP.read_text(encoding="utf-8"))
    assert existing_map["type"] == "canonical_identity_v13_map"
    assert existing_map["seal"]["sealed"] is True
    assert "universal-uuidv7-allocation.yaml" in PACKET.read_text(encoding="utf-8")
    assert "canonical owner path + structural pointer + entity" in PACKET.read_text(
        encoding="utf-8"
    )


def test_packet_names_the_current_relationship_deduplication_guard() -> None:
    source = (ROOT / "src" / "adr_kit" / "compiler" / "passes" / "derive_relationships.py").read_text(
        encoding="utf-8"
    )
    packet = PACKET.read_text(encoding="utf-8")

    assert "relationships: dict[str, RelationshipRecord]" in source
    assert "if rel_id in relationships:" in source
    assert "can collapse multiple source assertions" in packet
    assert re.search(r"relationship_id.{0,80}type:source:target", packet, re.DOTALL)
