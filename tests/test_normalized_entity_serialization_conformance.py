"""Cross-language conformance for Python-emitted normalized entity registries."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft7Validator, RefResolver
import pytest

from tests.conformance.generate_python_repository import generate_repository

ROOT = Path(__file__).resolve().parents[1]


def _canonical_errors(schema_path: Path, document: dict[str, object]) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    store = {schema["$id"]: schema}
    for sibling in schema_path.parent.glob("*.schema.json"):
        sibling_schema = json.loads(sibling.read_text(encoding="utf-8"))
        if "$id" in sibling_schema:
            store[sibling_schema["$id"]] = sibling_schema
    resolver = RefResolver(schema_path.as_uri(), schema, store=store)
    return [
        error.message for error in Draft7Validator(schema, resolver=resolver).iter_errors(document)
    ]


@pytest.mark.parametrize(
    ("authoring_version", "model_version"),
    [("1.4", "2.1"), ("1.5", "2.2")],
)
def test_public_python_compiler_emits_canonical_entity_registry(
    tmp_path: Path, authoring_version: str, model_version: str
) -> None:
    registry_path = generate_repository(
        tmp_path / f"v{model_version.replace('.', '_')}", authoring_version
    )
    emitted = yaml.safe_load(registry_path.read_bytes())

    assert emitted["schema_version"] == model_version
    assert emitted["type"] == "normalized_entity_registry"
    assert emitted["entities"]
    assert all("schema_version" not in entity for entity in emitted["entities"])
    assert (
        _canonical_errors(
            ROOT
            / f"schema/normalized-model/v{model_version}/normalized-entity-registry.schema.json",
            emitted,
        )
        == []
    )
