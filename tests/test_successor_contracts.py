"""Focused conformance for the additive authoring/normalization substrate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import rfc8785
from jsonschema import Draft7Validator, Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT / "schema" / "authoring" / "v1.7"
NORMALIZED = ROOT / "schema" / "normalized-model" / "v2.4"
INTERPRETATION = ROOT / "contracts" / "architecture-interpretation" / "v1.1"
UUID = "019109a0-b1c2-7def-8a00-112233445566"
UUID2 = "019109a0-b1c2-7def-8a00-112233445567"


def _document(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _authoring_validator(name: str) -> Draft7Validator:
    paths = list(AUTHORING.glob("*.json"))
    store: dict[str, dict] = {}
    for path in paths:
        document = _document(path)
        store[path.resolve().as_uri()] = document
        store[document["$id"]] = document
    path = AUTHORING / name
    document = _document(path)
    return Draft7Validator(
        document,
        resolver=RefResolver(path.resolve().as_uri(), document, store=store),
    )


def _root(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1.7",
        "id": UUID,
        "alias_name": "sample-adr",
        "title": "Sample ADR",
        "status": "proposed",
        "created_date": "2026-09-15",
        "authors": ["test"],
    }
    value.update(overrides)
    return value


def _component() -> dict[str, object]:
    return {
        "id": UUID,
        "alias_id": "COMP-0001",
        "alias_name": "sample-component",
        "name": "Sample component",
        "type": "service",
        "responsibilities": "Does sample work.",
        "generation_context": {"purpose": "Testing", "key_responsibilities": ["test"]},
        "interfaces": [
            {
                "id": UUID2,
                "alias_id": "IFACE-0001",
                "alias_name": "sample-interface",
                "type": "REST",
                "specification": "OpenAPI",
            }
        ],
    }


def _decision() -> dict[str, object]:
    return {"id": UUID2, "alias_id": "DEC-0001", "alias_name": "sample-decision", "summary": "Use the sample", "rationale": "It is explicit."}


def test_all_successor_json_resources_are_structurally_valid() -> None:
    for path in list(AUTHORING.glob("*.json")) + list(NORMALIZED.glob("*.json")):
        Draft7Validator.check_schema(_document(path))
    Draft202012Validator.check_schema(_document(INTERPRETATION / "schema.json"))
    for path in INTERPRETATION.rglob("*.json"):
        _document(path)


def test_all_three_authoring_roots_and_new_first_class_entities_validate() -> None:
    logical = _root(adr_type="logical", alias_id="ADR-L-0001", context="A bounded context.", decisions=[_decision()])
    physical_system = _root(
        adr_type="physical-system",
        alias_id="ADR-PS-0001",
        implements_logical=[UUID],
        context="A physical context.",
        technology_stack=[{"category": "language", "name": "Rust", "version": "1", "rationale": "test"}],
        system={"id": UUID2, "alias_id": "SYS-0001", "alias_name": "sample-system"},
        system_boundaries=[
            {"id": UUID, "alias_id": "SYSBOUND-0001", "alias_name": "sample-boundary", "name": "Boundary", "description": "Boundary"}
        ],
        data_flows=[
            {"id": UUID2, "alias_id": "FLOW-0001", "alias_name": "sample-flow", "name": "Flow", "description": "Flow"}
        ],
    )
    physical_component = _root(
        adr_type="physical-component",
        alias_id="ADR-PC-0001",
        implements_logical=[UUID],
        implements_system=[UUID2],
        context="A component context.",
        technology_stack=[{"category": "language", "name": "Rust", "version": "1", "rationale": "test"}],
        component_specifications=[_component()],
        implementation_decisions=[
            {"id": UUID2, "alias_id": "IMPL-0001", "alias_name": "sample-implementation", "summary": "Use Rust", "rationale": "Safety"}
        ],
    )
    assert not list(_authoring_validator("adr-logical.schema.json").iter_errors(logical))
    assert not list(_authoring_validator("adr-physical-system.schema.json").iter_errors(physical_system))
    assert not list(_authoring_validator("adr-physical-component.schema.json").iter_errors(physical_component))


def test_forward_identity_topology_and_exclusions_are_closed() -> None:
    topology = {
        "components": [{"topology_key": "TOPO-API", "component_ref": UUID, "purpose": "serve"}],
        "relationships": [{"from_key": "TOPO-API", "to_key": "TOPO-API", "type": "calls"}],
    }
    value = _root(
        adr_type="physical-system",
        alias_id="ADR-PS-0001",
        implements_logical=[UUID],
        context="A physical context.",
        technology_stack=[{"category": "language", "name": "Rust", "version": "1", "rationale": "test"}],
        system={"id": UUID2, "alias_id": "SYS-0001", "alias_name": "sample-system"},
        component_topology=topology,
    )
    assert not list(_authoring_validator("adr-physical-system.schema.json").iter_errors(value))
    bad_topology = json.loads(json.dumps(value))
    bad_topology["component_topology"]["relationships"][0] = {"from": "TOPO-API", "to": "TOPO-API", "type": "calls"}
    assert list(_authoring_validator("adr-physical-system.schema.json").iter_errors(bad_topology))
    forbidden = _root(adr_type="logical", alias_id="ADR-L-0001", context="context", decisions=[_decision()], constraints=[])
    assert list(_authoring_validator("adr-logical.schema.json").iter_errors(forbidden))


def test_np_and_custom_sources_require_their_locked_qualification() -> None:
    custom = {
        "id": UUID,
        "alias_id": "PAY-0001",
        "alias_name": "payment-policy",
        "entity_type": "payments:policy",
        "qualification": {"semantic_kind": "entity", "semantic_type": "payments:policy", "consumer_namespace": "payments", "contract_version": "1.0", "contract_fingerprint": "cecf:v1:sha256:" + "0" * 64},
        "properties": {"policy_code": "P1"},
        "rationale": "Consumer-qualified meaning.",
    }
    value = _root(adr_type="logical", alias_id="ADR-L-0001", context="context", decisions=[_decision()], extension_entities=[custom])
    assert not list(_authoring_validator("adr-logical.schema.json").iter_errors(value))
    bad_np = {"id": UUID, "alias_id": "NP-0001", "alias_name": "sample-np", "statement": "MUST", "normative_force": "MUST", "scope": "global", "lifecycle_stage": "active"}
    value["normative_propositions"] = [bad_np]
    assert list(_authoring_validator("adr-logical.schema.json").iter_errors(value))


def test_normalized_v24_preserves_first_class_np_and_relationship_modes() -> None:
    entity = {"id": UUID, "alias_id": "FLOW-0001", "alias_name": "sample-flow", "alias_ref": "FLOW-0001:sample-flow", "entity_type": "data_flow", "name": "Flow", "summary": "Flow", "uri": "adr://flow", "created_at": "2026-09-15T00:00:00Z", "entity_fingerprint": "sha256:" + "0" * 64, "lifecycle_stage": "active", "canonical_source": {}, "completeness": {}, "provenance": {}}
    np = {"id": UUID2, "alias_id": "NP-0001", "alias_name": "sample-np", "alias_ref": "NP-0001:sample-np", "entity_type": "normative_proposition", "name": "MUST", "summary": "MUST", "uri": "adr://np", "created_at": "2026-09-15T00:00:00Z", "entity_fingerprint": "sha256:" + "1" * 64, "statement": "MUST", "normative_force": "MUST", "scope": "global", "declaring_adr": {}, "source_artifact": {}, "source_contract": {}, "canonical_source": {}, "completeness": {}, "provenance": {}}
    document = {"schema_version": "2.4", "type": "normalized_entity_registry", "entities": [entity, np]}
    paths = list(NORMALIZED.glob("*.json"))
    store = {p.resolve().as_uri(): _document(p) for p in paths}
    store.update({_document(p)["$id"]: _document(p) for p in paths})
    schema_path = NORMALIZED / "normalized-entity-registry.schema.json"
    validator = Draft7Validator(_document(schema_path), resolver=RefResolver(schema_path.resolve().as_uri(), _document(schema_path), store=store))
    assert not list(validator.iter_errors(document))

    canonical = {"record_kind": "canonical", "id": UUID, "alias_id": "EXT-0001", "alias_name": "custom-edge", "relationship_type": "payments:depends_on", "from_entity_id": UUID, "to_entity_id": UUID2, "canonical_source_ref": "source#relationship", "custom_qualification": {"semantic_kind": "relationship", "semantic_type": "payments:depends_on", "consumer_namespace": "payments", "contract_version": "1.0", "contract_fingerprint": "cecf:v1:sha256:" + "2" * 64}}
    compatibility = {"record_kind": "compatibility", "relationship_id": "hash-not-canonical", "assertion_id": "asrt-" + "3" * 64, "relationship_type": "calls", "from_entity_id": UUID, "to_entity_id": UUID2, "provenance_classification": "explicit", "canonical_source_ref": "source#topology", "source_provenance": {"source_contract": "authoring@1.7", "source_pointer": "/component_topology/relationships/0"}}
    relationship_path = NORMALIZED / "relationship-record.schema.json"
    relationship_schema = _document(relationship_path)
    relationship_validator = Draft7Validator(relationship_schema, resolver=RefResolver(relationship_path.resolve().as_uri(), relationship_schema, store=store))
    assert not list(relationship_validator.iter_errors(canonical))
    assert not list(relationship_validator.iter_errors(compatibility))


def test_interpretation_covers_all_forward_types_and_resource_digests() -> None:
    contract = _document(INTERPRETATION / "contract.json")
    dispositions = {item["source"] for item in contract["forward_type_dispositions"]}
    assert len(dispositions) == 27
    assert {"entity/system_boundary", "entity/data_flow", "entity/evidence_expectation", "relationship/extension"} <= dispositions
    assert contract["public_boundary"] == {"advertised": False, "execution": "not_implemented", "selected_by_current_semantic_contract_set": False}
    for item in contract["resources"]:
        value = _document(INTERPRETATION / item["path"])
        digest = "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()
        assert digest == item["content_digest"]
