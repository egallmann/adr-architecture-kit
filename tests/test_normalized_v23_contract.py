"""Normalized-model v2.3 NP envelope and v2.2 regression tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, RefResolver
from pydantic import ValidationError

from adr_kit.models.v2_3 import NormalizedEntityRegistryV23

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema" / "normalized-model" / "v2.3"
UUID = "019109a0-b1c2-7def-8a00-112233445566"


def np_entity(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": UUID,
        "alias_id": "NP-0001",
        "alias_name": "explicit-contract",
        "alias_ref": "NP-0001:explicit-contract",
        "entity_type": "normative_proposition",
        "name": "The contract MUST remain explicit.",
        "summary": "The contract MUST remain explicit.",
        "uri": f"adr://kit/entities/{UUID}",
        "created_at": "2026-08-28T00:00:00Z",
        "entity_fingerprint": "sha256:" + "0" * 64,
        "statement": "The contract MUST remain explicit.",
        "normative_force": "MUST",
        "scope": "global",
        "declaring_adr": {
            "provider": "adr-kit",
            "id": UUID,
            "alias_id": "ADR-L-0001",
            "alias_name": "normative-authority",
        },
        "source_artifact": {
            "source_type": "logical_adr",
            "source_ref": "adr#np",
            "artifact_path": "adrs/logical/ADR-L-0001.yaml",
            "content_digest": "sha256:" + "1" * 64,
        },
        "source_contract": {
            "family": "authoring",
            "version": "1.6",
            "fingerprint": "sha256:" + "2" * 64,
        },
        "canonical_source": {
            "source_type": "logical_adr",
            "source_ref": "adr#np",
            "artifact_path": "adrs/logical/ADR-L-0001.yaml",
        },
        "completeness": {"status": "complete", "missing_fields": []},
        "provenance": {
            "source_type": "authoring",
            "source_ref": "1.6",
            "extraction_phase": "projection",
            "classification": "explicit",
            "generator": "test",
        },
    }
    value.update(overrides)
    return value


def test_v23_np_is_lifecycle_free_and_preserves_qualification() -> None:
    document = {
        "schema_version": "2.3",
        "type": "normalized_entity_registry",
        "entities": [np_entity()],
    }
    schema = json.loads(
        (SCHEMA_DIR / "normalized-entity-registry.schema.json").read_text(encoding="utf-8")
    )
    entity_schema = json.loads(
        (SCHEMA_DIR / "normalized-entity.schema.json").read_text(encoding="utf-8")
    )
    resolver = RefResolver(
        (SCHEMA_DIR / "normalized-entity-registry.schema.json").as_uri(),
        schema,
        store={entity_schema["$id"]: entity_schema},
    )
    assert list(Draft7Validator(schema, resolver=resolver).iter_errors(document)) == []
    parsed = NormalizedEntityRegistryV23.model_validate(document)
    assert parsed.entities[0].entity_type == "normative_proposition"
    assert not hasattr(parsed.entities[0], "lifecycle_stage")


@pytest.mark.parametrize("field", ["lifecycle_stage", "polarity", "status"])
def test_v23_np_rejects_independent_governance_fields(field: str) -> None:
    value = np_entity(**{field: "active"})
    with pytest.raises(ValidationError):
        NormalizedEntityRegistryV23.model_validate(
            {"schema_version": "2.3", "type": "normalized_entity_registry", "entities": [value]}
        )
