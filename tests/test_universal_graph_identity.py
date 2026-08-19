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
