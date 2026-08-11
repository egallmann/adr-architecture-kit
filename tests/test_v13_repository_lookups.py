"""R8 — model 2.0 repository lookup and alias deprecation tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import warnings
import yaml

from adr_kit.identity import (
    derive_alias_ref,
    derive_entity_uri,
    entity_fingerprint,
    uuidv7_created_at,
)
from adr_kit.repository import ArchitectureRegistryError, ArchitectureRepository

NAMESPACE = "arch-test"
UUID_A = "019109a0-b1c2-7def-8a00-112233445566"
UUID_B = "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
UUID_C = "019109a0-d5e6-7f78-8c00-aabb00112233"


def _provenance() -> dict[str, object]:
    return {
        "source_type": "test",
        "source_ref": "test",
        "extraction_phase": "test",
        "classification": "explicit",
        "generator": "test",
    }


def _canonical(ref: str) -> dict[str, object]:
    return {
        "source_type": "test",
        "source_ref": ref,
        "artifact_path": "adrs/logical/test.yaml",
    }


def _entity(
    *,
    uuid: str,
    alias_id: str,
    alias_name: str,
    entity_type: str,
    name: str,
) -> dict[str, object]:
    return {
        "id": uuid,
        "alias_id": alias_id,
        "alias_name": alias_name,
        "alias_ref": derive_alias_ref(alias_id, alias_name),
        "entity_type": entity_type,
        "name": name,
        "summary": name,
        "uri": derive_entity_uri(NAMESPACE, uuid),
        "created_at": uuidv7_created_at(uuid),
        "entity_fingerprint": entity_fingerprint(
            {
                "id": uuid,
                "alias_id": alias_id,
                "alias_name": alias_name,
                "entity_type": entity_type,
                "name": name,
            }
        ),
        "lifecycle_stage": "active",
        "canonical_source": _canonical(f"{alias_id}#{alias_id}"),
        "source_refs": [],
        "metadata": {"status": "accepted"},
        "relationships": {},
        "completeness": {"status": "complete", "missing_fields": []},
        "provenance": _provenance(),
    }


def _write_project(scope_root: Path, *, namespace: str = NAMESPACE) -> None:
    scope_root.mkdir(parents=True, exist_ok=True)
    (scope_root / "PROJECT.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "type: project_metadata",
                "project:",
                '  name: "arch-test"',
                "architecture_documentation:",
                '  adr_directory: "adrs/"',
                '  architecture_namespace: "' + namespace + '"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (scope_root / "adrs").mkdir(parents=True, exist_ok=True)


def _write_v2_bundle(
    scope_root: Path,
    entities: list[dict[str, object]],
    *,
    namespace: str = NAMESPACE,
) -> None:
    _write_project(scope_root, namespace=namespace)
    index_dir = scope_root / "adrs" / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    by_type: dict[str, list[dict[str, object]]] = {
        "component": [],
        "capability": [],
        "decision": [],
        "invariant": [],
        "system": [],
    }
    for entity in entities:
        entity_type = str(entity["entity_type"])
        if entity_type in by_type:
            by_type[entity_type].append(entity)

    def dump_registry(path: Path, payload_entities: list[dict[str, object]]) -> None:
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

    dump_registry(index_dir / "entity-registry.yaml", entities)
    dump_registry(index_dir / "component-registry.yaml", by_type["component"])
    dump_registry(index_dir / "capability-registry.yaml", by_type["capability"])
    dump_registry(index_dir / "decision-registry.yaml", by_type["decision"])
    dump_registry(index_dir / "invariant-registry.yaml", by_type["invariant"])
    dump_registry(index_dir / "system-registry.yaml", by_type["system"])

    (index_dir / "relationship-registry.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "2.0",
                "type": "relationship_registry",
                "relationships": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (index_dir / "unresolved-registry.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "2.0",
                "type": "unresolved_registry",
                "unresolved": [],
            },
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
                    "logical_adrs": 1,
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


def test_repository_loads_model_v2_bundle(tmp_path: Path) -> None:
    entities = [
        _entity(
            uuid=UUID_A,
            alias_id="ADR-L-1000",
            alias_name="discovery",
            entity_type="adr",
            name="Discovery",
        ),
        _entity(
            uuid=UUID_B,
            alias_id="CAP-1000",
            alias_name="validate",
            entity_type="capability",
            name="Validate",
        ),
    ]
    _write_v2_bundle(tmp_path, entities)

    repository = ArchitectureRepository(project_root=tmp_path)
    repository.load()

    assert repository.model_version == "2.0"
    model = repository.get_model_v2()
    assert model.architecture_namespace == NAMESPACE
    assert repository.find_entity_by_uuid(UUID_B) is not None
    assert repository.find_entity_by_alias_id("CAP-1000") is not None
    assert repository.find_entity_by_alias_ref("CAP-1000:validate") is not None
    assert repository.resolve_uri(derive_entity_uri(NAMESPACE, UUID_B)).id == UUID_B
    assert repository.resolve_entity_reference("CAP-1000") == UUID_B
    assert [item.alias_id for item in repository.list_aliases()] == ["ADR-L-1000", "CAP-1000"]


def test_find_entity_unique_alias_emits_deprecation_warning(tmp_path: Path) -> None:
    _write_v2_bundle(
        tmp_path,
        [
            _entity(
                uuid=UUID_A,
                alias_id="CAP-1000",
                alias_name="validate",
                entity_type="capability",
                name="Validate",
            )
        ],
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        entity = repository.find_entity("CAP-1000")

    assert entity is not None
    assert entity.id == UUID_A
    assert any(issubclass(item.category, DeprecationWarning) for item in caught)


def test_find_entity_ambiguous_alias_fails(tmp_path: Path) -> None:
    _write_v2_bundle(
        tmp_path,
        [
            _entity(
                uuid=UUID_A,
                alias_id="SHARED",
                alias_name="one",
                entity_type="capability",
                name="One",
            ),
            _entity(
                uuid=UUID_B,
                alias_id="SHARED",
                alias_name="two",
                entity_type="capability",
                name="Two",
            ),
        ],
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    with pytest.raises(ArchitectureRegistryError, match="Ambiguous alias_id"):
        repository.find_entity("SHARED")
