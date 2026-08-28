"""Authoring v1.5 and normalized model v2.2 contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator, RefResolver

ROOT = Path(__file__).resolve().parents[1]
AUTHORING_V15 = ROOT / "schema" / "authoring" / "v1.5"
NORMALIZED_V22 = ROOT / "schema" / "normalized-model" / "v2.2"
FIXTURES = ROOT / "tests" / "fixtures" / "authoring-v1.5-contract"


def _load_document(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(text)
        assert isinstance(loaded, dict)
        return loaded
    loaded = json.loads(text)
    assert isinstance(loaded, dict)
    return loaded


def _schema_store(schema_dir: Path) -> dict[str, dict]:
    store: dict[str, dict] = {}
    for schema_path in schema_dir.glob("*.schema.json"):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id")
        if schema_id:
            store[schema_id] = schema
    return store


def _validate(schema_path: Path, document: dict, *, extra_store_dirs: tuple[Path, ...] = ()) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    store = _schema_store(schema_path.parent)
    for extra_dir in extra_store_dirs:
        store.update(_schema_store(extra_dir))
    resolver = RefResolver(schema_path.as_uri(), schema, store=store)
    return [
        error.message for error in Draft7Validator(schema, resolver=resolver).iter_errors(document)
    ]


@pytest.mark.parametrize(
    ("fixture_name", "schema_name"),
    [
        ("valid-logical-alias.yaml", "adr-logical.schema.json"),
        ("valid-slim-topology-component.yaml", "adr-physical-system.schema.json"),
    ],
)
def test_authoring_v15_positive_fixtures(fixture_name: str, schema_name: str) -> None:
    document = _load_document(FIXTURES / fixture_name)
    errors = _validate(AUTHORING_V15 / schema_name, document)
    assert errors == [], errors


@pytest.mark.parametrize(
    ("fixture_name", "schema_name"),
    [
        ("invalid-logical-adr-p-alias.yaml", "adr-logical.schema.json"),
        ("invalid-ps-cross-type-alias.yaml", "adr-physical-system.schema.json"),
        ("invalid-topology-with-name.yaml", "adr-physical-system.schema.json"),
    ],
)
def test_authoring_v15_negative_fixtures(fixture_name: str, schema_name: str) -> None:
    document = _load_document(FIXTURES / fixture_name)
    errors = _validate(AUTHORING_V15 / schema_name, document)
    assert errors


def test_v22_relationship_record_positive_fixture() -> None:
    document = _load_document(FIXTURES / "valid-v22-relationship-record.json")
    errors = _validate(
        NORMALIZED_V22 / "relationship-record.schema.json",
        document,
        extra_store_dirs=(NORMALIZED_V22,),
    )
    assert errors == [], errors


def test_v22_relationship_record_rejects_topo_endpoint() -> None:
    document = _load_document(FIXTURES / "invalid-v22-topo-endpoint.json")
    errors = _validate(
        NORMALIZED_V22 / "relationship-record.schema.json",
        document,
        extra_store_dirs=(NORMALIZED_V22,),
    )
    assert errors


@pytest.mark.parametrize(
    ("schema_name", "adr_relpath"),
    [
        ("adr-physical-system.schema.json", "adrs/physical-system/ADR-PS-0001-adr-architecture-kit-discovery-and-indexing-system.yaml"),
        ("adr-physical-system.schema.json", "adrs/physical-system/ADR-PS-0002-adr-kit-compiler-and-validation-runtime.yaml"),
        ("adr-physical-component.schema.json", "adrs/physical-component/ADR-PC-0001-entity-registry-and-discovery-index.yaml"),
        ("adr-physical-component.schema.json", "adrs/physical-component/ADR-PC-0002-schema-and-contract-validation.yaml"),
        ("adr-physical-component.schema.json", "adrs/physical-component/ADR-PC-0003-compiler-pipeline-and-driver.yaml"),
        ("adr-physical-component.schema.json", "adrs/physical-component/ADR-PC-0008-project-scope-resolution.yaml"),
    ],
)
def test_promoted_v15_authority_documents_validate(schema_name: str, adr_relpath: str) -> None:
    document = _load_document(ROOT / adr_relpath)
    errors = _validate(AUTHORING_V15 / schema_name, document)
    assert errors == [], errors
