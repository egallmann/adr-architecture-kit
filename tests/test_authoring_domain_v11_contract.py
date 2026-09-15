"""ADC 1.1 descriptive contract closure tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
ADC10 = ROOT / "contracts/authoring-domain/v1.0/contract.json"
ADC11 = ROOT / "contracts/authoring-domain/v1.1/contract.json"
SCHEMA11 = ROOT / "contracts/authoring-domain/v1.1/schema.json"
CAPABILITIES = ROOT / "contracts/compatibility/host-capabilities.json"
ADC10_SHA256 = "b2de54a60b6f395dfc69a8ddb1b9707def18e5c93456607f947fc0af5d473c6a"
EXPECTED = {
    "adr/logical",
    "adr/physical-component",
    "adr/physical-system",
    "entity/boundary",
    "entity/capability",
    "entity/component",
    "entity/contract",
    "entity/data_flow",
    "entity/decision",
    "entity/evidence_expectation",
    "entity/extension",
    "entity/gap",
    "entity/implementation_decision",
    "entity/interface",
    "entity/invariant",
    "entity/normative_proposition",
    "entity/system",
    "entity/system_boundary",
    "relationship/calls",
    "relationship/depends_on",
    "relationship/extension",
    "relationship/publishes_to",
    "relationship/reads_from",
    "relationship/subscribes_to",
    "relationship/writes_to",
    "value/normative_force",
    "value/topology_component",
}
EXCLUDED = {
    "entity/constraint",
    "entity/nfr",
    "entity/requirement",
    "entity/integration",
    "relationship/consumes_interface",
    "relationship/composed_of",
    "relationship/provides_interface",
    "relationship/binds_substrate",
    "relationship/binds_rule",
    "relationship/expects_evidence",
}
POLICIES = (
    "construction_support",
    "input_contract",
    "identity_policy",
    "composition_policy",
    "reference_policy",
    "field_ownership_policy",
    "relationship_policy",
    "operation_posture",
    "ordering_policy",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def key(item: dict[str, Any]) -> str:
    return f"{item['key']['kind']}/{item['key']['name']}"


def catalog(path: Path) -> dict[str, dict[str, Any]]:
    return {key(item): item for item in load(path)["types"]}


def test_adc11_schema_and_exact_catalog() -> None:
    assert not list(Draft202012Validator(load(SCHEMA11)).iter_errors(load(ADC11)))
    assert set(catalog(ADC10)) == EXPECTED
    assert set(catalog(ADC11)) == EXPECTED
    assert len(catalog(ADC11)) == 27


def test_adc10_bytes_are_immutable() -> None:
    assert hashlib.sha256(ADC10.read_bytes()).hexdigest() == ADC10_SHA256
    assert (
        ADC10.read_bytes()
        == (ROOT / "src/adr_kit/compatibility/authoring-domain-v1.0.json").read_bytes()
    )


def test_adc11_closes_all_policy_dimensions() -> None:
    for type_key, descriptor in catalog(ADC11).items():
        for name in POLICIES:
            if name == "operation_posture":
                continue
            allowed = {"defined", "not_applicable"}
            if name == "construction_support":
                allowed |= {"described", "qualified_template"}
            assert descriptor[name]["status"] in allowed, f"{type_key}.{name}"
        assert set(descriptor["operation_posture"]) == {"create", "update", "reference", "retire"}
        assert all(
            value["status"] == "defined" for value in descriptor["operation_posture"].values()
        )
        assert descriptor["ordering_policy"]["status"] == "defined"
        required = {
            "allowed_outbound",
            "allowed_inbound",
            "semantic_owner",
            "relationship_mode",
            "relationship_field_contract",
            "cardinality",
            "ordering",
        }
        assert required <= set(descriptor["relationship_policy"]), f"{type_key}.relationship_policy"


def test_adc11_boundaries_and_truthful_capability() -> None:
    values = catalog(ADC11)
    assert not EXCLUDED.intersection(values)
    assert "relationship/consumes_interface" in set(load(ADC11)["excluded_from_version"])
    assert (
        values["relationship/extension"]["relationship_policy"]["relationship_mode"]
        == "custom_explicit"
    )
    assert (
        values["entity/normative_proposition"]["operation_posture"]["retire"]["permission"]
        == "unsupported"
    )
    assert "lifecycle" not in json.dumps(values["entity/normative_proposition"]).lower()
    assert values["value/normative_force"]["values"] == [
        "MUST",
        "MUST NOT",
        "SHOULD",
        "SHOULD NOT",
        "MAY",
    ]
    topology = values["value/topology_component"]
    assert topology["identity_policy"]["mode"] == "owner_local"
    assert topology["identity_policy"]["identity_bearing"] is False
    assert topology["forward_vocabulary"]["required_fields"] == [
        "topology_key",
        "from_key",
        "to_key",
    ]
    assert topology["forward_vocabulary"]["historical_identity"] == "not_authoritative"
    assert load(ADC11)["defined_capabilities"] == ["authoring.discovery"]
    capabilities = load(CAPABILITIES)["authoring_domain"]
    assert capabilities["supported_versions"] == ["1.0"]
    assert capabilities["preferred_version"] == "1.0"
    assert capabilities["capabilities"] == ["authoring.discovery"]
    assert not any("construct" in value for value in capabilities["operations"])
