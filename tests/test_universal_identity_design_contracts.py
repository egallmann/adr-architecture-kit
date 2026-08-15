from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "docs" / "design-journal" / "2026-universal-uuidv7-entity-identity.md"
COLLISIONS = (
    ROOT
    / "docs"
    / "design-journal"
    / "2026-universal-uuidv7-alias-collision-disposition.yaml"
)
FIXTURE = ROOT / "tests" / "fixtures" / "universal-graph-identity-baseline.json"


def _journal() -> str:
    return JOURNAL.read_text(encoding="utf-8")


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_design_closure_records_exhaustive_identity_and_ontology_contracts() -> None:
    text = _journal()

    required_sections = (
        "## Identity classification matrix",
        "## Relationship and assertion ontology",
        "## Alias namespaces and collision policy",
        "## Family-scoped semantic version map",
        "## Graph/projection vNext contract",
        "## Sealed universal UUID allocation-map contract",
        "## Migration gates and non-goals",
    )
    for section in required_sections:
        assert section in text

    required_matrix_rows = (
        "| ADR documents |",
        "| requirements snapshots |",
        "| effective relationships |",
        "| relationship assertions |",
        "| generated registry records |",
        "| graph nodes |",
        "| graph edges |",
        "| effective inverse traversal |",
        "| local helper structures |",
    )
    for row in required_matrix_rows:
        assert row in text

    for phrase in (
        "ENTITY",
        "VALUE_OBJECT",
        "DERIVED_PROJECTION",
        "One effective relationship may therefore have multiple assertions",
        "It does not\nreceive a second canonical UUID",
        "relationship_id",
        "assertion_id",
        "schema/authoring/v2.0/",
        "schema/normalized-model/v3.0/",
        "schema/architecture-discovery/v2.0/",
        "package version 0.4.1",
        "does not mint UUIDs",
        "open a PR",
    ):
        assert phrase in text


def test_collision_disposition_is_complete_for_known_legacy_collisions_and_not_sealed() -> None:
    document = yaml.safe_load(COLLISIONS.read_text(encoding="utf-8"))
    expected_aliases = {"CONST-0001", "GAP-0001", "GAP-0002", "GAP-0003", "GAP-0004"}
    collisions = document["collisions"]

    assert document["classification"] == "DESIGN-CLOSURE-REVIEW-ARTIFACT"
    assert {item["legacy_alias"] for item in collisions} == expected_aliases
    assert all(item["status"] == "REQUIRES-HUMAN-REVIEW" for item in collisions)
    assert all(len(item["claims"]) >= 2 for item in collisions)
    assert document["resolution_gate"] == {
        "all_claims_mapped": True,
        "selected_incumbents_reviewed": False,
        "final_aliases_allocated": False,
        "retired_aliases_recorded": False,
        "map_sealing_allowed": False,
    }


def test_fixture_remains_a_verification_snapshot_over_the_admitted_checkpoint() -> None:
    fixture = _fixture()
    graph = fixture["architecture_graph"]

    assert fixture["classification"] == "NON-AUTHORITATIVE VERIFICATION SNAPSHOT"
    assert fixture["governing_adr"] == "ADR-L-0022"
    assert fixture["baseline_sha"] == "614b678"
    assert graph["baseline_identity_evidence"] == {
        "uuidv7_nodes": graph["node_count"],
        "nodes_with_alias_envelope": 0,
        "uuidv7_edges": 0,
        "edges_with_alias_envelope": 0,
    }
    assert graph["node_semantic_sha256"]
    assert graph["edge_semantic_sha256"]
    assert len(fixture["graph_eligible_corpus_records"]) == 40
