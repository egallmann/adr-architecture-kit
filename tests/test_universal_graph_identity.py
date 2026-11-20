from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

UUIDV7_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "universal-graph-identity-baseline.json"
ADR_L0042_PATH = "adrs/logical/ADR-L-0042-release-version-and-semantic-capability-milestones.yaml"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _semantic_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _resolve_pointer(document: Any, pointer: str) -> Any:
    value = document
    if pointer == "/":
        return value
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def _uuid_errors(record: dict[str, Any], location: str) -> list[str]:
    errors: list[str] = []
    if not UUIDV7_RE.fullmatch(str(record.get("id", ""))):
        errors.append(f"{location}: id is not UUIDv7")
    return errors


def test_identity_inventory_is_explicitly_non_authoritative_and_unique() -> None:
    fixture = _fixture()

    assert fixture["classification"] == "NON-AUTHORITATIVE VERIFICATION SNAPSHOT"
    assert fixture["governing_adr"] == "ADR-L-0022"
    locations = [
        (item["path"], item["pointer"]) for item in fixture["graph_eligible_corpus_records"]
    ]
    assert len(locations) == 35
    assert len(locations) == len(set(locations))


def test_architecture_graph_preserves_baseline_semantics_and_uses_entity_identity() -> None:
    fixture = _fixture()["architecture_graph"]
    graph = yaml.safe_load((_repo_root() / fixture["path"]).read_text(encoding="utf-8"))
    nodes = graph["nodes"]
    edges = graph["edges"]

    adr_l0042 = yaml.safe_load((_repo_root() / ADR_L0042_PATH).read_text(encoding="utf-8"))
    expected_additions = {
        adr_l0042["id"]: ("adr", adr_l0042["title"]),
        **{
            decision["id"]: ("decision", decision["summary"])
            for decision in adr_l0042["decisions"]
        },
        **{
            invariant["id"]: ("invariant", invariant["alias_id"])
            for invariant in adr_l0042["invariants"]
        },
    }
    added_nodes = [
        node
        for node in nodes
        if (node.get("canonical_source") or {}).get("artifact_path") == ADR_L0042_PATH
    ]
    assert {
        node["id"]: (node["entity_type"], node["name"]) for node in added_nodes
    } == expected_additions

    added_ids = set(expected_additions)
    baseline_nodes = [node for node in nodes if node["id"] not in added_ids]
    baseline_edges = [
        edge
        for edge in edges
        if edge.get("source_entity_id") not in added_ids
        and edge.get("target_entity_id") not in added_ids
    ]
    added_edges = [
        edge
        for edge in edges
        if edge.get("source_entity_id") in added_ids or edge.get("target_entity_id") in added_ids
    ]

    node_semantics = [
        {key: node.get(key) for key in ("id", "entity_type", "name", "canonical_source")}
        for node in baseline_nodes
    ]
    edge_semantics = [
        {
            key: edge.get(key)
            for key in (
                "assertion_id",
                "relationship_type",
                "source_entity_id",
                "target_entity_id",
                "provenance_classification",
                "evidence",
                "canonical_source_ref",
                "confidence",
                "metadata",
            )
        }
        for edge in baseline_edges
    ]

    # The identity snapshot remains sealed to ADR-L-0022's historical checkpoint.
    # Verify that checkpoint as a subset, then admit only this ADR's exact additive graph.
    assert len(baseline_nodes) == fixture["node_count"]
    assert len(baseline_edges) == fixture["edge_count"]
    assert Counter(node["entity_type"] for node in baseline_nodes) == fixture["node_types"]
    assert Counter(edge["relationship_type"] for edge in baseline_edges) == fixture["edge_types"]
    assert _semantic_sha256(node_semantics) == fixture["node_semantic_sha256"]
    assert _semantic_sha256(edge_semantics) == fixture["edge_semantic_sha256"]

    assert len(nodes) == fixture["node_count"] + len(expected_additions)
    assert len(edges) == fixture["edge_count"] + 24
    assert Counter(edge["relationship_type"] for edge in added_edges) == {
        "declared_in": 8,
        "references": 4,
        "refines": 12,
    }
    assert all(
        edge.get("canonical_source_ref", "").startswith(adr_l0042["id"])
        for edge in added_edges
    )

    errors: list[str] = []
    for index, node in enumerate(nodes):
        errors.extend(_uuid_errors(node, f"nodes[{index}]"))
    for index, edge in enumerate(edges):
        errors.extend(
            _uuid_errors(
                {"id": edge.get("source_entity_id")},
                f"edges[{index}].source_entity_id",
            )
        )
        errors.extend(
            _uuid_errors(
                {"id": edge.get("target_entity_id")},
                f"edges[{index}].target_entity_id",
            )
        )
    assert not errors, "\n".join(errors[:50])


def test_graph_eligible_corpus_records_remain_legacy_until_migration_gate() -> None:
    """The admitted graph identity does not silently migrate authoring sources."""
    errors: list[str] = []
    for item in _fixture()["graph_eligible_corpus_records"]:
        path = _repo_root() / item["path"]
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        record = _resolve_pointer(document, item["pointer"])
        location = f"{item['path']}#{item['pointer']}"
        if not isinstance(record, dict):
            errors.append(f"{location}: expected an object")
            continue
        legacy_alias = item["legacy_alias"]
        if legacy_alias:
            if record.get("id") != legacy_alias:
                errors.append(f"{location}: source id must preserve legacy alias {legacy_alias!r}")
        elif "id" in record:
            errors.append(f"{location}: owner-local source record must not gain an id")
        if "alias_id" in record or "alias_name" in record:
            errors.append(
                f"{location}: source identity envelope requires the reviewed migration gate"
            )

    assert not errors, "\n".join(errors)
