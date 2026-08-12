"""R8 — provider registry namespace/URI resolution tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from adr_kit.identity import (
    derive_alias_ref,
    derive_entity_uri,
    entity_fingerprint,
    uuidv7_created_at,
)
from adr_kit.repository import ArchitectureRegistryError, ProviderRegistry

UUID_A = "019109a0-b1c2-7def-8a00-112233445566"
UUID_B = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"


def _entity(namespace: str, uuid: str, alias_id: str, alias_name: str) -> dict[str, object]:
    return {
        "id": uuid,
        "alias_id": alias_id,
        "alias_name": alias_name,
        "alias_ref": derive_alias_ref(alias_id, alias_name),
        "entity_type": "capability",
        "name": alias_name,
        "summary": alias_name,
        "uri": derive_entity_uri(namespace, uuid),
        "created_at": uuidv7_created_at(uuid),
        "entity_fingerprint": entity_fingerprint(
            {
                "id": uuid,
                "alias_id": alias_id,
                "alias_name": alias_name,
                "entity_type": "capability",
                "name": alias_name,
            }
        ),
        "lifecycle_stage": "active",
        "canonical_source": {
            "source_type": "test",
            "source_ref": alias_id,
            "artifact_path": "adrs/logical/test.yaml",
        },
        "source_refs": [],
        "metadata": {},
        "relationships": {},
        "completeness": {"status": "complete", "missing_fields": []},
        "provenance": {
            "source_type": "test",
            "source_ref": "test",
            "extraction_phase": "test",
            "classification": "explicit",
            "generator": "test",
        },
    }


def _write_provider(root: Path, *, namespace: str, entities: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "PROJECT.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: project_metadata",
                "project:",
                f'  name: "{namespace}"',
                "architecture_documentation:",
                '  adr_directory: "adrs/"',
                f'  architecture_namespace: "{namespace}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    index_dir = root / "adrs" / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    def dump(path: Path, payload_entities: list[dict[str, object]]) -> None:
        path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": "2.0",
                    "type": "normalized_entity_registry",
                    "entities": payload_entities,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    dump(index_dir / "entity-registry.yaml", entities)
    for name in (
        "component-registry.yaml",
        "capability-registry.yaml",
        "decision-registry.yaml",
        "invariant-registry.yaml",
        "system-registry.yaml",
    ):
        subset = [e for e in entities if e["entity_type"] == name.split("-", 1)[0]]
        if name.startswith("capability"):
            subset = [e for e in entities if e["entity_type"] == "capability"]
        elif name.startswith("component"):
            subset = [e for e in entities if e["entity_type"] == "component"]
        elif name.startswith("decision"):
            subset = [e for e in entities if e["entity_type"] == "decision"]
        elif name.startswith("invariant"):
            subset = [e for e in entities if e["entity_type"] == "invariant"]
        elif name.startswith("system"):
            subset = [e for e in entities if e["entity_type"] == "system"]
        dump(index_dir / name, subset)

    (index_dir / "relationship-registry.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": "2.0", "type": "relationship_registry", "relationships": []},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (index_dir / "unresolved-registry.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": "2.0", "type": "unresolved_registry", "unresolved": []},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (index_dir / "architecture-index.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.1",
                "type": "architecture_index",
                "architecture_namespace": namespace,
                "generated_at": now,
                "generator": "test",
                "entity_registry_path": "adrs/index/entity-registry.yaml",
                "relationship_registry_path": "adrs/index/relationship-registry.yaml",
                "unresolved_registry_path": "adrs/index/unresolved-registry.yaml",
                "decision_registry_path": "adrs/index/decision-registry.yaml",
                "capability_registry_path": "adrs/index/capability-registry.yaml",
                "invariant_registry_path": "adrs/index/invariant-registry.yaml",
                "component_registry_path": "adrs/index/component-registry.yaml",
                "system_registry_path": "adrs/index/system-registry.yaml",
                "validation_summary": {
                    "hard_failures": 0,
                    "warnings": 0,
                    "unresolved_entries": 0,
                },
                "source_coverage": {
                    "logical_adrs": 0,
                    "physical_adrs": 0,
                    "physical_system_adrs": 0,
                    "physical_component_adrs": 0,
                    "standalone_invariants": 0,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_provider_registry_routes_by_architecture_namespace(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    _write_provider(
        left,
        namespace="ns-left",
        entities=[_entity("ns-left", UUID_A, "CAP-LEFT", "left-cap")],
    )
    _write_provider(
        right,
        namespace="ns-right",
        entities=[_entity("ns-right", UUID_B, "CAP-RIGHT", "right-cap")],
    )

    registry = ProviderRegistry.from_workspace_roots({"left": left, "right": right})

    assert registry.resolve_entity("ns-left", UUID_A).alias_id == "CAP-LEFT"
    assert registry.resolve_entity("ns-right", UUID_B).alias_id == "CAP-RIGHT"
    assert registry.resolve_uri(derive_entity_uri("ns-left", UUID_A)).id == UUID_A


def test_provider_registry_rejects_duplicate_namespaces(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    _write_provider(
        left, namespace="same-ns", entities=[_entity("same-ns", UUID_A, "CAP-A", "alpha")]
    )
    _write_provider(
        right, namespace="same-ns", entities=[_entity("same-ns", UUID_B, "CAP-B", "bravo")]
    )

    with pytest.raises(ArchitectureRegistryError, match="Duplicate architecture_namespace"):
        ProviderRegistry.from_workspace_roots({"left": left, "right": right})


def test_provider_registry_rejects_wrong_namespace_uri(tmp_path: Path) -> None:
    root = tmp_path / "only"
    _write_provider(root, namespace="ns-a", entities=[_entity("ns-a", UUID_A, "CAP-A", "alpha")])
    registry = ProviderRegistry.from_workspace_roots({"only": root})

    with pytest.raises(ArchitectureRegistryError, match="Unknown architecture_namespace"):
        registry.resolve_uri(derive_entity_uri("ns-other", UUID_A))
