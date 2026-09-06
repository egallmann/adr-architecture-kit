"""Python qualification against the shared Consumer Binding Contract 1.0 corpus."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, RefResolver

from adr_kit.semantic_extensions import ExtensionValidationError, validate_property_map

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "contracts" / "conformance" / "consumer-binding-v1"


def _load(relative: str) -> dict[str, object]:
    return json.loads((CORPUS / relative).read_text(encoding="utf-8"))


def _validate(schema_path: Path, document: dict[str, object]) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    store = {schema.get("$id", schema_path.as_uri()): schema}
    for sibling in schema_path.parent.glob("*.schema.json"):
        sibling_schema = json.loads(sibling.read_text(encoding="utf-8"))
        if sibling_schema.get("$id"):
            store[sibling_schema["$id"]] = sibling_schema
    resolver = RefResolver(schema_path.as_uri(), schema, store=store)
    return [
        error.message for error in Draft7Validator(schema, resolver=resolver).iter_errors(document)
    ]


def test_manifest_is_static_and_declares_contract() -> None:
    manifest = _load("manifest.json")
    assert manifest["contract_version"] == "ADR-Kit Consumer Binding Contract 1.0"
    assert manifest["fingerprint_rule"] == "binding_local_determinism_only"
    assert len(manifest["fixtures"]) == 10


def test_normalized_model_fixture_is_schema_valid_and_semantically_preserved() -> None:
    fixture = _load("repository/model-v21.json")
    errors = _validate(
        ROOT / "schema/normalized-model/v2.1/normalized-architecture-model.schema.json",
        fixture["input"],
    )
    assert errors == []
    expected = fixture["expected_observable_semantic_result"]
    assert expected["relationship_record_kinds"] == ["canonical", "compatibility"]
    assert expected["extension_boolean_array"] == [True, False]
    assert expected["fingerprint_comparison"] == "not_required_across_bindings"


def test_boolean_array_extension_values_align_with_canonical_schema() -> None:
    fixture = _load("semantic-extensions/qualified-unknown.json")
    assert (
        validate_property_map(fixture["input"]["extension"]["properties"])
        == fixture["input"]["extension"]["properties"]
    )


def test_core_entity_extension_is_rejected_by_shared_schema() -> None:
    fixture = _load("semantic-extensions/core-extension-invalid.json")
    errors = _validate(
        ROOT / "schema/normalized-model/v2.1/normalized-entity.schema.json", fixture["input"]
    )
    assert errors
    assert (
        fixture["expected_observable_semantic_result"]["stable_code"]
        == "contract.extension_core_entity"
    )


def test_python_extension_validator_rejects_non_scalar_arrays() -> None:
    with pytest.raises(ExtensionValidationError):
        validate_property_map({"nested": [{"not": "scalar"}]})


@pytest.mark.parametrize(
    ("relative", "schema"),
    [
        (
            "embodiment-linkage/evidence-v15.json",
            "schema/evidence-attribution/v1.5/implementation-attribution-evidence.schema.json",
        ),
        (
            "embodiment-linkage/evidence-v16.json",
            "schema/evidence-attribution/v1.6/implementation-attribution-evidence.schema.json",
        ),
    ],
)
def test_evidence_fixtures_are_valid_for_their_advertised_versions(
    relative: str, schema: str
) -> None:
    fixture = _load(relative)
    assert _validate(ROOT / schema, fixture["input"]) == []


def test_v16_enforces_confidence_restriction_is_explicit() -> None:
    fixture = _load("embodiment-linkage/evidence-v16-enforces-inferred.json")
    errors = _validate(
        ROOT / "schema/evidence-attribution/v1.6/implementation-attribution-evidence.schema.json",
        fixture["input"],
    )
    assert errors
    assert (
        fixture["expected_observable_semantic_result"]["stable_code"]
        == "attribution.v16_enforces_confidence"
    )
