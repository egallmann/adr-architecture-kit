"""Frozen authority checks for Architecture Interpretation 1.2 publication."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

import rfc8785
from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import (
    calculate_semantic_contract_fingerprint,
    get_semantic_contract,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]
AI11 = ROOT / "contracts" / "architecture-interpretation" / "v1.1"
AI12 = ROOT / "contracts" / "architecture-interpretation" / "v1.2"
AUTHORING = ROOT / "schema" / "authoring" / "v1.7"
SEMANTIC = ROOT / "contracts" / "semantic-contract" / "v1.0"
BUNDLED = ROOT / "src" / "adr_kit" / "semantic_contract" / "v1_0"
DISPOSITION_CLASSES = {
    "direct_semantic_value",
    "canonical_field_placement",
    "compatibility_projection",
    "declared_absence",
    "deterministic_ceremony",
}


def _read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _resource_path(directory: Path, key: str) -> Path:
    parts = key.split("/")
    candidates = [key.replace("/", "-") + ".json"]
    if len(parts) == 3:
        candidates.append(f"{parts[0]}-{parts[2]}.json")
    for name in candidates:
        path = directory / name
        if path.is_file():
            return path
    raise FileNotFoundError(key)


def _pointer(document: Any, pointer: str) -> Any:
    if not pointer:
        return document
    assert pointer.startswith("/")
    value = document
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def _resolve_schema_selector(selector: str) -> Any:
    filename, pointer = selector.split("#", 1)
    return _pointer(_read(AUTHORING / filename), pointer)


def _properties(schema: dict[str, Any], filename: str) -> set[str]:
    result = set(schema.get("properties", {}))
    for index, child in enumerate(schema.get("allOf", [])):
        if "$ref" in child:
            reference = child["$ref"]
            ref_file, fragment = reference.split("#", 1) if "#" in reference else (reference, "")
            target = _pointer(_read(AUTHORING / ref_file), fragment)
            result.update(_properties(target, ref_file))
        else:
            result.update(_properties(child, filename))
    return result


def _supported_type_keys() -> set[str]:
    decoding = _read(AI12 / "resources" / "source-decoding-1.7.json")
    values = decoding["forward_authorable"]
    return {
        *(f"adr/{name}" for name in values["adr"]),
        *(f"entity/{name}" for name in values["entity"]),
        *(f"relationship/{name}" for name in values["relationship"]),
        *(f"value/{name}" for name in values["value"]),
    }


def test_ai12_is_a_valid_independently_fingerprinted_contract_with_closed_resource_dependencies() -> (
    None
):
    contract = _read(AI12 / "contract.json")
    schema = _read(AI12 / "schema.json")
    assert not list(Draft202012Validator(schema).iter_errors(contract))
    assert contract["semanticContractVersion"] == "1.2"
    assert (
        calculate_semantic_contract_fingerprint(contract).semantic_contract_fingerprint
        == contract["semanticContractFingerprint"]
    )
    assert verify_semantic_contract(contract).success is True
    resources = [
        {
            "canonicalResourceKey": item["canonicalResourceKey"],
            "content": _read(_resource_path(SEMANTIC / "resources", item["canonicalResourceKey"])),
        }
        for item in contract["resourceManifest"]
    ]
    closure = validate_semantic_resource_closure(contract, resources)
    assert closure.success is True
    assert closure.closure_valid is True
    assert contract["frozenNormativeConformanceResources"] == [
        "architecture-interpretation/1.2/conformance"
    ]
    for item in contract["resourceManifest"]:
        resource = next(
            r["content"]
            for r in resources
            if r["canonicalResourceKey"] == item["canonicalResourceKey"]
        )
        assert "contentDigest" in item
        assert (
            item["contentDigest"] == "sha256:" + hashlib.sha256(rfc8785.dumps(resource)).hexdigest()
        )
        assert isinstance(item["dependencies"], list)
        assert load_semantic_resource(item["canonicalResourceKey"]) == resource
    conformance = _read(AI12 / "resources" / "conformance.json")
    conformance_schema = _read(AI12 / "resources" / "conformance.schema.json")
    assert not list(Draft202012Validator(conformance_schema).iter_errors(conformance))


def test_ai12_field_inventory_is_closed_unique_and_resolves_every_authoring_schema_field() -> None:
    inventory = _read(AI12 / "resources" / "field-dispositions-1.7-to-2.4.json")
    inventory_schema = _read(AI12 / "resources" / "field-dispositions.schema.json")
    assert not list(Draft202012Validator(inventory_schema).iter_errors(inventory))
    type_entries = inventory["semantic_types"]
    assert {entry["semantic_type"] for entry in type_entries} == _supported_type_keys()
    assert len(type_entries) == len(_supported_type_keys())
    counts: Counter[str] = Counter()

    for type_entry in type_entries:
        semantic_type = type_entry["semantic_type"]
        filename, schema_pointer = type_entry["source_schema"].split("#", 1)
        source_schema = _pointer(_read(AUTHORING / filename), schema_pointer)
        fields = type_entry["field_dispositions"]
        keys = [field["semantic_field_key"] for field in fields]
        assert len(keys) == len(set(keys)), semantic_type
        assert all(key.startswith(semantic_type + "#") for key in keys)
        assert len(fields) == len({field["schema_selector"] for field in fields})
        assert all(field["disposition"] in DISPOSITION_CLASSES for field in fields)
        counts.update(field["disposition"] for field in fields)
        for field in fields:
            # Every selector is an exact location in the committed Authoring 1.7 schema closure.
            selected = _resolve_schema_selector(field["schema_selector"])
            assert isinstance(selected, dict) or semantic_type == "value/normative_force"
            # Runtime pointers never participate in the key.
            assert field["source_instance_pointer"] == "provenance_only"
            assert "/*/" not in field["semantic_field_key"] or "/items/" in field["schema_selector"]

        if semantic_type.startswith("adr/"):
            expected_properties = _properties(source_schema, filename)
            expected_keys = {
                semantic_type + "#/" + name.replace("~", "~0").replace("/", "~1")
                for name in expected_properties
            }
            if semantic_type == "adr/physical-system":
                expected_keys.remove(semantic_type + "#/component_topology")
                expected_keys |= {
                    semantic_type + "#/component_topology/components",
                    semantic_type + "#/component_topology/relationships",
                }
            assert expected_keys == set(keys), semantic_type
        elif semantic_type.startswith("entity/") or semantic_type == "relationship/extension":
            expected_properties = set(source_schema.get("properties", {}))
            expected_keys = {
                semantic_type + "#/" + name.replace("~", "~0").replace("/", "~1")
                for name in expected_properties
            }
            assert expected_keys == set(keys), semantic_type

    assert set(counts) <= DISPOSITION_CLASSES
    assert sum(counts.values()) == sum(len(entry["field_dispositions"]) for entry in type_entries)
    assert counts["direct_semantic_value"] > 0
    assert counts["canonical_field_placement"] > 0
    assert counts["compatibility_projection"] > 0
    assert counts["deterministic_ceremony"] > 0
    assert inventory["declared_absences"] == [
        {
            "semantic_field_key": "entity/normative_proposition#/lifecycle_stage",
            "source_schema_presence": "forbidden by Authoring 1.7 normative_proposition schema",
            "normalized_location": "normalized-model@2.4 normative_proposition#/lifecycle_stage",
            "governing_rule": "architecture-interpretation/1.2/rules#normative_proposition_lifecycle_free",
            "meaning": "Normative propositions are declaration-only semantic units and have no lifecycle value; this is a declared absence, not an omitted supported source field.",
        }
    ]


def test_ai12_semantic_extensions_detached_context_ordering_and_provenance_are_explicit() -> None:
    inventory = _read(AI12 / "resources" / "field-dispositions-1.7-to-2.4.json")
    rules = _read(AI12 / "resources" / "rules.json")
    detached = _read(AI12 / "resources" / "detached-context.json")
    gap = next(
        item for item in inventory["semantic_types"] if item["semantic_type"] == "entity/gap"
    )
    context = next(
        item
        for item in gap["field_dispositions"]
        if item["semantic_field_key"] == "entity/gap#/context"
    )
    assert context["disposition"] == "direct_semantic_value"
    assert "metadata.semantic_extensions" in context["normalized_destination"]
    assert context["source_instance_pointer"] == "provenance_only"
    assert rules["semantic_extensions"]["value"] == "complete typed JSON value without coercion"
    assert rules["provenance"]["source_semantics_rule"].startswith(
        "metadata.source_semantics is replay/provenance evidence"
    )
    assert rules["ordering_and_multiplicity"]["default"].startswith(
        "Arrays have no semantic order solely because they are JSON arrays"
    )
    assert (
        "entity/data_flow#/path is an ordered owner-local topology-key path."
        in rules["ordering_and_multiplicity"]["ordered_values"]
    )
    assert detached["domain"] == "adr-kit.detached-candidate-normalization/v1"
    assert detached["provider_kind"] == "adr-kit-detached-candidate"
    assert detached["architecture_namespace"] == "urn:adr-kit:detached-candidate:v1"
    assert (
        detached["scope_root_form"]
        == "urn:adr-kit:detached-candidate:v1:source-basis:sha256:<lowercase-basis-digest>"
    )
    assert detached["root_artifact_locator_form"].endswith(
        "/root:sha256:<SHA-256-of-UTF-8-source_ref>"
    )
    assert "repository_path" in detached["identity_distinctions"]
    assert "persistence" in detached["forbidden_implications"]
    assert all(
        case["expected"] in {"conforms", "rejects", "preserves", "excludes", "matches"}
        for case in _read(AI12 / "resources" / "conformance.json")["cases"]
    )


def test_ai12_mirror_and_historical_authorities_remain_separate() -> None:
    contract = _read(AI12 / "contract.json")
    definition_name = "architecture-interpretation-1.2.json"
    assert (SEMANTIC / "definitions" / definition_name).read_bytes() == (
        BUNDLED / "definitions" / definition_name
    ).read_bytes()
    for entry in contract["resourceManifest"]:
        key = entry["canonicalResourceKey"]
        assert (
            _resource_path(SEMANTIC / "resources", key).read_bytes()
            == _resource_path(BUNDLED / "resources", key).read_bytes()
        )
    ai11 = _read(AI11 / "contract.json")
    assert (
        ai11["semanticContractFingerprint"]
        == "scf:v1:sha256:3650db1f6763a1e7ab81a3f3663d002b3e97ffc0ae007bd7d3543508c069100e"
    )
    assert (
        get_semantic_contract("architecture-interpretation", "1.1").semantic_contract_fingerprint
        == ai11["semanticContractFingerprint"]
    )
    assert (
        get_semantic_contract("architecture-interpretation", "1.2").semantic_contract_fingerprint
        == contract["semanticContractFingerprint"]
    )
    current = _read(SEMANTIC / "current" / "semantic-contract-current-1.0.json")
    current_set = _read(
        SEMANTIC / "sets" / (current["semanticContractSetId"].replace(":", "-") + ".json")
    )
    assert (
        current["semanticContractSetId"]
        == "scs:v1:sha256:d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6"
    )
    assert current["semanticContractSetId"] == current_set["semanticContractSetId"]
    assert not any(
        member["semanticContractVersion"] == "1.2"
        and member["semanticContractFamily"] == "architecture-interpretation"
        for member in current_set["members"]
    )
    assert (
        _read(ROOT / "contracts" / "authoring-construction" / "v1.0" / "contract.json")[
            "semanticContractFingerprint"
        ]
        == "scf:v1:sha256:b94f67ebff64b6560206715cef87a49b4444b71aa661cce92a6c3d04d8bf2703"
    )
    assert not (ROOT / "contracts" / "authoring-construction" / "v1.1").exists()
