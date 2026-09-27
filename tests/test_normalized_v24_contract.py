"""Normalized-model v2.4 schema-only validation and packaging coverage."""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path

import pytest
from adr_kit.parser import ADRParser, ADRSchemaValidationError

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "schema" / "normalized-model" / "v2.4"
NAMES = (
    "normalized-architecture-model.schema.json",
    "normalized-entity-registry.schema.json",
    "normalized-entity.schema.json",
    "relationship-record.schema.json",
    "relationship-registry.schema.json",
    "unresolved-registry.schema.json",
)
UUID = "019109a0-b1c2-7def-8a00-112233445566"


def entity() -> dict[str, object]:
    return {
        "id": UUID,
        "alias_id": "SYS-0001",
        "alias_name": "platform-system",
        "alias_ref": "SYS-0001:platform-system",
        "entity_type": "system",
        "name": "Platform system",
        "summary": "A platform system.",
        "uri": "adr://kit/entities/019109a0-b1c2-7def-8a00-112233445566",
        "created_at": "2026-09-27T00:00:00Z",
        "entity_fingerprint": "sha256:" + "0" * 64,
        "lifecycle_stage": "active",
        "canonical_source": {"source_type": "test", "source_ref": "test#system"},
        "completeness": {"status": "complete"},
        "provenance": {"source_type": "test", "source_ref": "test#system"},
    }


def relationship() -> dict[str, object]:
    return {
        "record_kind": "canonical",
        "id": "019109a0-b1c2-7def-8a00-223344556677",
        "alias_id": "REL-0001",
        "alias_name": "platform-calls-platform",
        "relationship_type": "calls",
        "from_entity_id": UUID,
        "to_entity_id": "019109a0-b1c2-7def-8a00-223344556677",
        "canonical_source_ref": "test#relationship",
    }


def root() -> dict[str, object]:
    return {
        "schema_version": "2.4",
        "type": "normalized_architecture_model",
        "mode": "normalized",
        "scope_root": "test",
        "fingerprint": "sha256:" + "1" * 64,
        "entities": [entity()],
        "relationships": [relationship()],
        "unresolved": [{"code": "missing-source", "message": "Source is unavailable."}],
    }


def test_v24_canonical_resources_are_byte_identical_in_python_package() -> None:
    for name in NAMES:
        canonical = (CANONICAL / name).read_bytes()
        packaged = resources.files("adr_kit.schema.v2_4").joinpath(name).read_bytes()
        assert hashlib.sha256(packaged).digest() == hashlib.sha256(canonical).digest()


def test_v24_root_and_registries_validate_with_canonical_refs() -> None:
    parser = ADRParser()
    parser.validate_against_schema(root(), "normalized_architecture_model_v2_4")
    assert (
        parser.parse_normalized_entity_registry_from_data(
            json.dumps(
                {
                    "schema_version": "2.4",
                    "type": "normalized_entity_registry",
                    "entities": [entity()],
                }
            )
        )["schema_version"]
        == "2.4"
    )
    assert (
        parser.parse_relationship_registry_from_data(
            json.dumps(
                {
                    "schema_version": "2.4",
                    "type": "relationship_registry",
                    "relationships": [relationship()],
                }
            )
        )["schema_version"]
        == "2.4"
    )
    assert (
        parser.parse_unresolved_registry_from_data(
            json.dumps(
                {
                    "schema_version": "2.4",
                    "type": "unresolved_registry",
                    "unresolved": [{"code": "missing", "message": "Missing."}],
                }
            )
        )["schema_version"]
        == "2.4"
    )


@pytest.mark.parametrize(
    ("schema_name", "document"),
    [
        ("normalized_architecture_model_v2_4", {**root(), "schema_version": "2.3"}),
        (
            "normalized_entity_registry_v2_4",
            {
                "schema_version": "2.4",
                "type": "normalized_entity_registry",
                "entities": [{"entity_type": "system"}],
            },
        ),
        (
            "relationship_registry_v2_4",
            {
                "schema_version": "2.4",
                "type": "relationship_registry",
                "relationships": [{"record_kind": "canonical"}],
            },
        ),
        (
            "unresolved_registry_v2_4",
            {
                "schema_version": "2.4",
                "type": "unresolved_registry",
                "unresolved": [{"code": "Bad Code", "message": "bad"}],
            },
        ),
    ],
)
def test_v24_rejects_malformed_documents(schema_name: str, document: dict[str, object]) -> None:
    with pytest.raises(ADRSchemaValidationError):
        ADRParser().validate_against_schema(document, schema_name)
