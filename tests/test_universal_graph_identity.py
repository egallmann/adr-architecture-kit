from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


UUIDV7_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
ALIAS_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{4}$")
ALIAS_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "universal-graph-identity-baseline.json"


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


def _identity_errors(record: dict[str, Any], location: str) -> list[str]:
    errors: list[str] = []
    if not UUIDV7_RE.fullmatch(str(record.get("id", ""))):
        errors.append(f"{location}: id is not UUIDv7")
    alias_id = str(record.get("alias_id", ""))
    if not ALIAS_ID_RE.fullmatch(alias_id):
        errors.append(f"{location}: alias_id is missing or not governed")
    alias_name = str(record.get("alias_name", ""))
    if not ALIAS_NAME_RE.fullmatch(alias_name) or not 3 <= len(alias_name) <= 96:
        errors.append(f"{location}: alias_name is missing or not governed")
    return errors


def test_identity_inventory_is_explicitly_non_authoritative_and_unique() -> None:
    fixture = _fixture()

    assert fixture["classification"] == "NON-AUTHORITATIVE VERIFICATION SNAPSHOT"
    assert fixture["governing_adr"] == "ADR-L-0022"
    locations = [
        (item["path"], item["pointer"])
        for item in fixture["graph_eligible_corpus_records"]
    ]
    assert len(locations) == 40
    assert len(locations) == len(set(locations))


def test_architecture_graph_preserves_baseline_semantics_and_uses_entity_identity() -> None:
    fixture = _fixture()["architecture_graph"]
    graph = yaml.safe_load((_repo_root() / fixture["path"]).read_text(encoding="utf-8"))
    nodes = graph["nodes"]
    edges = graph["edges"]

    node_semantics = [
        {key: node.get(key) for key in ("id", "entity_type", "name", "canonical_source")}
        for node in nodes
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
        for edge in edges
    ]

    assert len(nodes) == fixture["node_count"]
    assert len(edges) == fixture["edge_count"]
    assert Counter(node["entity_type"] for node in nodes) == fixture["node_types"]
    assert Counter(edge["relationship_type"] for edge in edges) == fixture["edge_types"]
    assert _semantic_sha256(node_semantics) == fixture["node_semantic_sha256"]
    assert _semantic_sha256(edge_semantics) == fixture["edge_semantic_sha256"]

    errors: list[str] = []
    for index, node in enumerate(nodes):
        errors.extend(_identity_errors(node, f"nodes[{index}]"))
    for index, edge in enumerate(edges):
        relationship = {"id": edge.get("relationship_id"), **edge}
        errors.extend(_identity_errors(relationship, f"edges[{index}]"))
    assert not errors, "\n".join(errors[:50])


def test_all_known_graph_eligible_corpus_records_have_entity_identity() -> None:
    errors: list[str] = []
    for item in _fixture()["graph_eligible_corpus_records"]:
        path = _repo_root() / item["path"]
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        record = _resolve_pointer(document, item["pointer"])
        location = f"{item['path']}#{item['pointer']}"
        if not isinstance(record, dict):
            errors.append(f"{location}: expected an object")
            continue
        errors.extend(_identity_errors(record, location))
        legacy_alias = item["legacy_alias"]
        if legacy_alias and record.get("alias_id") != legacy_alias:
            errors.append(
                f"{location}: alias_id must preserve legacy alias {legacy_alias!r}"
            )

    assert not errors, "\n".join(errors)
