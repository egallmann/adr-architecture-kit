"""Focused conformance coverage for the descriptive Custom Entity Contract 1.0."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/custom-entity/v1.0/contract.json"
SCHEMA = ROOT / "contracts/custom-entity/v1.0/schema.json"
FIXTURE = ROOT / "tests/fixtures/custom-entity-v1.0/valid-observation-registry.json"
INVALID_UNQUALIFIED = ROOT / "tests/fixtures/custom-entity-v1.0/invalid-unqualified-type.json"
INVALID_LATEST = ROOT / "tests/fixtures/custom-entity-v1.0/invalid-latest-selection.json"
INVALID_DUPLICATE = ROOT / "tests/fixtures/custom-entity-v1.0/invalid-ambiguous-duplicate.json"
ADC10 = ROOT / "contracts/authoring-domain/v1.0/contract.json"
CAPABILITIES = ROOT / "contracts/compatibility/host-capabilities.json"
ADC10_SHA256 = "b2de54a60b6f395dfc69a8ddb1b9707def18e5c93456607f947fc0af5d473c6a"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def errors(document: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(load(SCHEMA))
    return [error.message for error in validator.iter_errors(document)]


def qualification(definition: dict[str, Any]) -> tuple[str, str, str]:
    return (
        definition["semantic_kind"],
        definition["semantic_type"],
        definition["contract_version"],
    )


def reject_ambiguous_duplicates(definitions: list[dict[str, Any]]) -> None:
    seen: dict[tuple[str, str, str], str] = {}
    for definition in definitions:
        key = qualification(definition)
        fingerprint = definition["contract_fingerprint"]
        previous = seen.get(key)
        if previous is not None and previous != fingerprint:
            raise ValueError(f"ambiguous custom contract qualification: {key}")
        seen[key] = fingerprint


def registry_for(definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "registry_id": "example.consumer.custom-entity-registry",
        "registry_version": "1.0",
        "authority": "consumer_namespace",
        "definitions": [definition],
        "selection_policy": {
            "mode": "exact_qualified_selection",
            "latest": "forbidden",
            "missing_exact_authority": "reject",
            "ambiguous_duplicate": "reject",
            "ordering": "canonical_semantic_json",
        },
        "exact_selection": {
            "semantic_kind": definition["semantic_kind"],
            "semantic_type": definition["semantic_type"],
            "contract_version": definition["contract_version"],
            "contract_fingerprint": definition["contract_fingerprint"],
        },
    }


def test_contract_schema_and_positive_registry_validate() -> None:
    schema = load(SCHEMA)
    Draft202012Validator.check_schema(schema)
    assert errors(load(CONTRACT)) == []
    assert errors(load(FIXTURE)) == []


def test_qualification_is_exact_for_entity_and_relationship() -> None:
    contract = load(CONTRACT)
    fixture = load(FIXTURE)
    definitions = fixture["definitions"]
    assert {item["semantic_kind"] for item in definitions} == {"entity", "relationship"}
    for definition in definitions:
        assert ":" in definition["semantic_type"]
        assert definition["semantic_type"].startswith(definition["consumer_namespace"] + ":")
        assert definition["contract_version"] == "1.0"
        assert definition["contract_fingerprint"].startswith("scf:v1:sha256:")
    assert contract["qualification_policy"] == {
        "semantic_kinds": ["entity", "relationship"],
        "semantic_type_format": "consumer_namespace:local_name",
        "required_components": [
            "semantic_kind",
            "semantic_type",
            "consumer_namespace",
            "contract_version",
            "contract_fingerprint",
        ],
        "path_identity": False,
        "ambient_defaults": False,
        "latest_selection": False,
    }


def test_unqualified_and_latest_authority_are_rejected() -> None:
    assert errors(load(INVALID_UNQUALIFIED))
    assert errors(load(INVALID_LATEST))
    assert load(INVALID_LATEST)["exact_selection"]["contract_version"] == "latest"


def test_registry_rejects_ambiguous_duplicate_but_retains_exact_duplicate() -> None:
    fixture = load(FIXTURE)
    entity = fixture["definitions"][0]
    exact_duplicate = copy.deepcopy(entity)
    reject_ambiguous_duplicates([entity, exact_duplicate])

    conflicting = load(INVALID_DUPLICATE)
    assert qualification(conflicting["definitions"][0]) == qualification(
        conflicting["definitions"][1]
    )
    assert (
        conflicting["definitions"][0]["contract_fingerprint"]
        != conflicting["definitions"][1]["contract_fingerprint"]
    )
    try:
        reject_ambiguous_duplicates(conflicting["definitions"])
    except ValueError:
        pass
    else:
        raise AssertionError("conflicting exact custom qualification was accepted")

    registry_policy = load(CONTRACT)["registry_policy"]
    assert registry_policy["retained_versions"] == "explicit_historical_versions"
    assert registry_policy["selection"] == "exact_type_kind_version_fingerprint"
    assert registry_policy["global_registry"] is False


def test_identity_alias_and_existence_semantics_are_closed() -> None:
    contract = load(CONTRACT)
    fixture = load(FIXTURE)
    for definition in fixture["definitions"]:
        identity = definition["identity_policy"]
        assert identity["mode"] == "canonical_uuidv7"
        assert identity["identity_bearing"] is True
        assert identity["supplied_identity"] == "preserve"
        assert identity["update_identity"] == "preserve"
        assert identity["reference_identity"] == "reuse"
        assert identity["composition_identity"] == "does_not_manufacture"
        assert "hash" in identity["forbidden_derivations"]
        assert definition["alias_policy"]["fields"] == ["alias_id", "alias_name"]
        assert definition["alias_policy"]["canonical_foreign_key"] is False

    entity = fixture["definitions"][0]
    assert entity["existence_policy"]["values"] == ["active", "retired"]
    assert entity["consumer_state_policy"]["separate_from_existence"] is True
    assert entity["consumer_state_policy"]["replacement_of_existence_state"] is False
    assert contract["identity_policy"]["create"] == "may_mint_when_absent_without_admission"


def test_fields_composition_and_property_values_are_bounded() -> None:
    fixture = load(FIXTURE)
    entity, relationship = fixture["definitions"]
    assert entity["field_contract"]["unknown_field_policy"] == "reject"
    assert set(entity["field_contract"]["forbidden_fields"]) >= {
        "topology_key",
        "from_key",
        "to_key",
    }
    assert entity["composition_policy"]["allowed_parents"] == ["adr/logical"]
    assert relationship["property_policy"] == {
        "value_semantics": "bounded_scalar_or_scalar_array",
        "unknown_property_policy": "reject",
        "nested_objects": False,
        "relationship_effect": "never_implies_graph_relationship",
        "max_properties": 16,
        "array_max_items": 8,
    }

    unbounded = copy.deepcopy(entity)
    unbounded["field_contract"]["fields"]["arbitrary_metadata"] = {"type": "object"}
    assert errors(registry_for(unbounded))


def test_relationship_is_explicit_and_supports_canonical_and_custom_endpoints() -> None:
    fixture = load(FIXTURE)
    relationship = fixture["definitions"][1]
    assert relationship["relationship_mode"] == "custom_explicit"
    assert relationship["field_contract"]["required_fields"] == [
        "id",
        "alias_id",
        "alias_name",
        "relationship_type",
        "from_entity_id",
        "to_entity_id",
        "properties",
        "rationale",
    ]
    assert relationship["reference_policy"]["reference_fields"] == [
        "from_entity_id",
        "to_entity_id",
    ]
    assert relationship["reference_policy"]["endpoint_representation"] == "canonical_uuidv7"
    assert relationship["reference_policy"]["allowed_reference_kinds"] == [
        "canonical_entity",
        "qualified_custom_type",
    ]
    assert relationship["field_contract"]["forbidden_fields"] == [
        "topology_key",
        "from_key",
        "to_key",
    ]
    assert (
        relationship["property_policy"]["relationship_effect"] == "never_implies_graph_relationship"
    )
    assert relationship["cardinality"]["mode"] == "custom_contract_declared"
    assert relationship["ordering"]["materiality"] == "material_when_declared"

    canonical = {"endpoint_kind": "canonical_entity", "semantic_type": "entity/capability"}
    custom = {"endpoint_kind": "qualified_custom_type", "semantic_type": "example:observation"}
    for source in (canonical, custom):
        for target in (canonical, custom):
            candidate = copy.deepcopy(relationship)
            candidate["source_types"] = [source]
            candidate["target_types"] = [target]
            assert errors(registry_for(candidate)) == []
    assert load(CONTRACT)["relationship_policy"]["endpoint_legality"] == (
        "exact_custom_contract_declared_source_and_target_types"
    )


def test_operations_migration_promotion_and_read_only_boundary_are_descriptive() -> None:
    contract = load(CONTRACT)
    operations = contract["operation_semantics"]
    assert operations["execution"] == "not_implemented_in_contract_definition_slice"
    for operation in ("create", "update", "retire"):
        assert operations[operation]["permission"] == "qualified_contract_required"
        assert operations[operation]["qualification"] == "exact_type_version_fingerprint"
    assert operations["create"]["persistence"] == "not_authorized"
    assert "contract-version change is explicit migration" in " ".join(
        operations["update"]["rules"]
    )
    assert contract["migration_policy"]["mode"] == "explicit_contract_migration"
    assert contract["migration_policy"]["source"] == "exact_type_version_fingerprint"
    assert contract["migration_policy"]["target"] == "exact_type_version_fingerprint"
    assert contract["canonical_promotion_policy"]["same_referent_identity"] == "preserve_uuidv7"
    assert contract["read_only_boundary"] == {
        "descriptive_only": True,
        "construct_authoring_set": False,
        "validate_authoring": False,
        "custom_operations": False,
        "registry_execution": False,
        "persistence": False,
        "runtime": False,
        "capability_advertisement": False,
    }


def test_historical_bytes_and_public_capability_remain_unchanged() -> None:
    assert hashlib.sha256(ADC10.read_bytes()).hexdigest() == ADC10_SHA256
    capabilities = load(CAPABILITIES)["authoring_domain"]
    assert capabilities["supported_versions"] == ["1.0"]
    assert capabilities["preferred_version"] == "1.0"
    assert capabilities["capabilities"] == ["authoring.discovery"]
    assert not any("custom" in operation for operation in capabilities["operations"])
