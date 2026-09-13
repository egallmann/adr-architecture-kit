"""Cross-language ADC 1.0 discovery contract checks for the Python binding."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from adr_kit import api

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "contracts" / "authoring-domain" / "v1.0" / "contract.json"
CORPUS = (
    ROOT
    / "contracts"
    / "conformance"
    / "consumer-binding-v1"
    / "authoring-discovery"
    / "authoring-discovery-v1.json"
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _canonical() -> dict[str, Any]:
    return json.loads(CANONICAL.read_text(encoding="utf-8"))


def _corpus() -> dict[str, Any]:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def _descriptor_wire(value: Any) -> dict[str, Any]:
    """Normalize explicit DTO defaults back to the canonical optional fields."""

    result = _jsonable(asdict(value))
    for policy_name in (
        "input_contract",
        "identity_policy",
        "composition_policy",
        "reference_policy",
        "field_ownership_policy",
    ):
        policy = result[policy_name]
        if policy["mode"] is None:
            policy.pop("mode")
        if not policy["values"]:
            policy.pop("values")
        if (
            policy_name != "composition_policy" or policy["status"] == "not_applicable"
        ) and not policy["allowed_parents"]:
            policy.pop("allowed_parents")
        if policy["owner"] is None:
            policy.pop("owner")
    discriminator = result["discriminator"]
    if discriminator["field"] is None:
        discriminator.pop("field")
    if discriminator["value"] is None:
        discriminator.pop("value")
    return result


def test_python_discovery_matches_canonical_contract_and_shared_corpus() -> None:
    contract = _canonical()
    corpus = _corpus()["expected_observable_semantic_results"]

    assert _jsonable(asdict(api.describe_authoring_contract("1.0"))) == corpus["describe_contract"]
    listed = api.list_authoring_types("1.0")
    assert len(listed.types) == 27
    assert _jsonable(asdict(listed)) == corpus["list_types"]
    assert _jsonable(asdict(listed)) == {
        "contract_version": contract["contract_version"],
        "types": [
            {
                "key": item["key"],
                "display_name": item["display_name"],
                "description": item["description"],
            }
            for item in sorted(
                contract["types"], key=lambda value: (value["key"]["kind"], value["key"]["name"])
            )
        ],
    }


def test_python_discovery_exact_kind_filter_and_order() -> None:
    result = api.list_authoring_types("1.0", kind="entity")
    assert result.contract_version == "1.0"
    assert len(result.types) == 15
    assert [(item.key.kind, item.key.name) for item in result.types] == sorted(
        (item.key.kind, item.key.name) for item in result.types
    )
    assert all(item.key.kind == "entity" for item in result.types)


@pytest.mark.parametrize(
    ("kind", "name"),
    (
        ("adr", "logical"),
        ("entity", "decision"),
        ("entity", "normative_proposition"),
        ("entity", "invariant"),
        ("entity", "extension"),
        ("relationship", "calls"),
        ("relationship", "extension"),
        ("value", "normative_force"),
        ("value", "topology_component"),
    ),
)
def test_python_descriptor_is_complete_canonical_projection(kind: str, name: str) -> None:
    canonical = next(
        item for item in _canonical()["types"] if item["key"] == {"kind": kind, "name": name}
    )
    descriptor = api.describe_authoring_type("1.0", kind=kind, name=name)
    assert _descriptor_wire(descriptor) == canonical


@pytest.mark.parametrize(
    ("call", "code", "path"),
    (
        (
            lambda: api.describe_authoring_contract("2.0"),
            "contract.unsupported_version",
            "contract_version",
        ),
        (
            lambda: api.list_authoring_types("1.0", kind="Entity"),
            "authoring.unknown_type_kind",
            "kind",
        ),
        (
            lambda: api.describe_authoring_type("1.0", kind="entity", name="missing"),
            "authoring.unknown_type",
            "name",
        ),
        (
            lambda: api.describe_authoring_type("1.0", kind="entity", name="Decision"),
            "authoring.unknown_type",
            "name",
        ),
        (
            lambda: api.describe_authoring_type("1.0", kind="entity", name="logical"),
            "authoring.unknown_type",
            "name",
        ),
    ),
)
def test_python_discovery_preserves_deterministic_diagnostics(
    call: Any, code: str, path: str
) -> None:
    with pytest.raises(api.AuthoringDiscoveryError) as raised:
        call()
    assert raised.value.code == code
    assert [(item.code, item.path) for item in raised.value.diagnostics] == [(code, path)]


def test_python_discovery_objects_are_immutable_and_do_not_admit_mutation() -> None:
    descriptor = api.describe_authoring_type("1.0", kind="value", name="normative_force")
    assert descriptor.input_contract.status == "defined"
    assert descriptor.input_contract.values == ("MUST", "MUST NOT", "SHOULD", "SHOULD NOT", "MAY")
    with pytest.raises((AttributeError, TypeError)):
        descriptor.input_contract.status = "deferred"
    assert not any(
        name.startswith(
            ("create_", "construct_", "author_", "mutate_", "save_", "persist_", "update_")
        )
        for name in api.__all__
    )


def test_python_authoring_mirror_is_byte_exact() -> None:
    mirror = ROOT / "src" / "adr_kit" / "compatibility" / "authoring-domain-v1.0.json"
    assert mirror.read_bytes() == CANONICAL.read_bytes()


def test_python_capabilities_advertise_qualified_authoring_discovery() -> None:
    manifest = api.capabilities()
    assert manifest.supported_authoring_domain_versions == ("1.0",)
    assert manifest.preferred_authoring_domain_version == "1.0"
    assert manifest.authoring_capabilities == ("authoring.discovery",)
