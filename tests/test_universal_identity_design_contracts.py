from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "adrs" / "logical" / "ADR-L-0022-universal-uuidv7-entity-identity.yaml"
FIXTURE = ROOT / "tests" / "fixtures" / "universal-graph-identity-baseline.json"


def _adr() -> dict[str, object]:
    return yaml.safe_load(ADR.read_text(encoding="utf-8"))


def _fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _authority_text(document: dict[str, object]) -> str:
    parts = [str(document.get("context", "")), str(document.get("notes", ""))]
    for section in ("decisions", "invariants"):
        for item in document.get(section, []):
            parts.extend(
                str(item.get(field, "")) for field in ("summary", "rationale", "statement")
            )
    return "\n".join(parts)


def test_durable_adr_records_universal_identity_and_ontology_contracts() -> None:
    document = _adr()
    decisions = {item["alias_id"]: item for item in document["decisions"]}
    invariants = {item["alias_id"]: item for item in document["invariants"]}
    text = _authority_text(document)

    for alias_id in (
        "DEC-0130",
        "DEC-0131",
        "DEC-0132",
        "DEC-0133",
        "DEC-0134",
        "DEC-0135",
        "DEC-0136",
        "DEC-0137",
        "DEC-0138",
        "DEC-0139",
        "DEC-0140",
        "DEC-0141",
        "DEC-0142",
        "DEC-0143",
        "DEC-0144",
        "DEC-0145",
        "DEC-0146",
    ):
        assert alias_id in decisions
    for alias_id in (
        "INV-0130",
        "INV-0131",
        "INV-0132",
        "INV-0133",
        "INV-0134",
        "INV-0135",
        "INV-0136",
        "INV-0137",
        "INV-0138",
        "INV-0139",
        "INV-0140",
    ):
        assert alias_id in invariants

    for phrase in (
        "ENTITY",
        "VALUE_OBJECT",
        "DERIVED_PROJECTION",
        "effective relationship",
        "relationship assertion",
        "relationship_id",
        "assertion_id",
        "inverse traversal",
        "family-scoped",
        "graph-vNext",
        "allocation map",
        "SEALED",
        "human approval",
        "local design journals and review packets are non-authoritative",
    ):
        assert phrase in text

    assert "docs/design-journal/2026-universal-uuidv7-entity-identity.md" not in text


def test_fixture_remains_a_verification_snapshot_over_the_admitted_checkpoint() -> None:
    fixture = _fixture()
    graph = fixture["architecture_graph"]

    assert fixture["classification"] == "NON-AUTHORITATIVE VERIFICATION SNAPSHOT"
    assert fixture["governing_adr"] == "ADR-L-0022"
    assert fixture["baseline_sha"] == "b998bfc"
    assert graph["baseline_identity_evidence"] == {
        "uuidv7_nodes": graph["node_count"],
        "nodes_with_alias_envelope": 0,
        "uuidv7_edges": 0,
        "edges_with_alias_envelope": 0,
    }
    assert graph["node_semantic_sha256"]
    assert graph["edge_semantic_sha256"]
    assert len(fixture["graph_eligible_corpus_records"]) == 35
