"""Focused conformance for the additive authoring/normalization substrate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import rfc8785
from jsonschema import Draft7Validator, Draft202012Validator, RefResolver
from adr_kit.semantic_contract import (
    calculate_semantic_contract_fingerprint,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]
AUTHORING = ROOT / "schema" / "authoring" / "v1.7"
NORMALIZED = ROOT / "schema" / "normalized-model" / "v2.4"
INTERPRETATION = ROOT / "contracts" / "architecture-interpretation" / "v1.1"
UUID = "019109a0-b1c2-7def-8a00-112233445566"
UUID2 = "019109a0-b1c2-7def-8a00-112233445567"


def _document(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _authoring_validator(name: str) -> Draft7Validator:
    paths = list(AUTHORING.glob("*.json"))
    store: dict[str, Any] = {}
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


def _authoring_definition_validator(reference: str) -> Draft7Validator:
    schema_name, fragment = reference.split("#", 1)
    paths = list(AUTHORING.glob("*.json"))
    store: dict[str, Any] = {}
    for path in paths:
        document = _document(path)
        store[path.resolve().as_uri()] = document
        store[document["$id"]] = document
    path = AUTHORING / schema_name
    document = _document(path)
    schema = {"$ref": f"{document['$id']}#{fragment}"}
    return Draft7Validator(
        schema,
        resolver=RefResolver(path.resolve().as_uri(), document, store=store),
    )


def _normalized_validator(name: str) -> Draft7Validator:
    paths = list(NORMALIZED.glob("*.json"))
    store: dict[str, Any] = {}
    for path in paths:
        document = _document(path)
        store[path.resolve().as_uri()] = document
        store[document["$id"]] = document
    path = NORMALIZED / name
    document = _document(path)
    return Draft7Validator(
        document,
        resolver=RefResolver(path.resolve().as_uri(), document, store=store),
    )


def _custom_qualification_is_exact(
    instance: dict[str, Any], type_field: str, qualification: dict[str, Any]
) -> bool:
    semantic_type = qualification.get("semantic_type")
    namespace = semantic_type.split(":", 1)[0] if isinstance(semantic_type, str) else None
    return (
        qualification.get("semantic_kind")
        == ("entity" if type_field == "entity_type" else "relationship")
        and instance.get(type_field) == semantic_type
        and namespace == qualification.get("consumer_namespace")
        and isinstance(qualification.get("contract_version"), str)
        and isinstance(qualification.get("contract_fingerprint"), str)
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
    return {
        "id": UUID2,
        "alias_id": "DEC-0001",
        "alias_name": "sample-decision",
        "summary": "Use the sample",
        "rationale": "It is explicit.",
    }


def test_all_successor_json_resources_are_structurally_valid() -> None:
    for path in list(AUTHORING.glob("*.json")) + list(NORMALIZED.glob("*.json")):
        Draft7Validator.check_schema(_document(path))
    Draft202012Validator.check_schema(_document(INTERPRETATION / "schema.json"))
    for path in INTERPRETATION.rglob("*.json"):
        _document(path)


def test_all_three_authoring_roots_and_new_first_class_entities_validate() -> None:
    logical = _root(
        adr_type="logical",
        alias_id="ADR-L-0001",
        context="A bounded context.",
        decisions=[_decision()],
    )
    physical_system = _root(
        adr_type="physical-system",
        alias_id="ADR-PS-0001",
        implements_logical=[UUID],
        context="A physical context.",
        technology_stack=[
            {"category": "language", "name": "Rust", "version": "1", "rationale": "test"}
        ],
        system={"id": UUID2, "alias_id": "SYS-0001", "alias_name": "sample-system"},
        system_boundaries=[
            {
                "id": UUID,
                "alias_id": "SYSBOUND-0001",
                "alias_name": "sample-boundary",
                "name": "Boundary",
                "description": "Boundary",
            }
        ],
        data_flows=[
            {
                "id": UUID2,
                "alias_id": "FLOW-0001",
                "alias_name": "sample-flow",
                "name": "Flow",
                "description": "Flow",
            }
        ],
    )
    physical_component = _root(
        adr_type="physical-component",
        alias_id="ADR-PC-0001",
        implements_logical=[UUID],
        implements_system=[UUID2],
        context="A component context.",
        technology_stack=[
            {"category": "language", "name": "Rust", "version": "1", "rationale": "test"}
        ],
        component_specifications=[_component()],
        implementation_decisions=[
            {
                "id": UUID2,
                "alias_id": "IMPL-0001",
                "alias_name": "sample-implementation",
                "summary": "Use Rust",
                "rationale": "Safety",
            }
        ],
    )
    assert not list(_authoring_validator("adr-logical.schema.json").iter_errors(logical))
    assert not list(
        _authoring_validator("adr-physical-system.schema.json").iter_errors(physical_system)
    )
    assert not list(
        _authoring_validator("adr-physical-component.schema.json").iter_errors(physical_component)
    )


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
        technology_stack=[
            {"category": "language", "name": "Rust", "version": "1", "rationale": "test"}
        ],
        system={"id": UUID2, "alias_id": "SYS-0001", "alias_name": "sample-system"},
        component_topology=topology,
    )
    assert not list(_authoring_validator("adr-physical-system.schema.json").iter_errors(value))
    bad_topology = json.loads(json.dumps(value))
    bad_topology["component_topology"]["relationships"][0] = {
        "from": "TOPO-API",
        "to": "TOPO-API",
        "type": "calls",
    }
    assert list(_authoring_validator("adr-physical-system.schema.json").iter_errors(bad_topology))


def test_forward_authoring_has_no_untyped_binding_escape_hatches() -> None:
    for path in AUTHORING.glob("*.json"):
        properties = _document(path).get("properties", {})
        assert "substrate_bindings" not in properties
        assert "rule_bindings" not in properties

    decoding = _document(INTERPRETATION / "resources" / "source-decoding-1.7.json")
    assert set(decoding["unsupported_forward_fields"]) == {
        "substrate_bindings",
        "rule_bindings",
    }
    forbidden = _root(
        adr_type="logical",
        alias_id="ADR-L-0001",
        context="context",
        decisions=[_decision()],
        constraints=[],
    )
    assert list(_authoring_validator("adr-logical.schema.json").iter_errors(forbidden))


def test_np_and_custom_sources_require_their_locked_qualification() -> None:
    custom = {
        "id": UUID,
        "alias_id": "PAY-0001",
        "alias_name": "payment-policy",
        "entity_type": "payments:policy",
        "qualification": {
            "semantic_kind": "entity",
            "semantic_type": "payments:policy",
            "consumer_namespace": "payments",
            "contract_version": "1.0",
            "contract_fingerprint": "cecf:v1:sha256:" + "0" * 64,
        },
        "properties": {"policy_code": "P1"},
        "rationale": "Consumer-qualified meaning.",
    }
    value = _root(
        adr_type="logical",
        alias_id="ADR-L-0001",
        context="context",
        decisions=[_decision()],
        extension_entities=[custom],
    )
    assert not list(_authoring_validator("adr-logical.schema.json").iter_errors(value))
    bad_np = {
        "id": UUID,
        "alias_id": "NP-0001",
        "alias_name": "sample-np",
        "statement": "MUST",
        "normative_force": "MUST",
        "scope": "global",
        "lifecycle_stage": "active",
    }
    value["normative_propositions"] = [bad_np]
    assert list(_authoring_validator("adr-logical.schema.json").iter_errors(value))


def test_authoring_custom_qualification_is_semantically_exact() -> None:
    entity = {
        "id": UUID,
        "alias_id": "PAY-0001",
        "alias_name": "payment-policy",
        "entity_type": "payments:policy",
        "qualification": {
            "semantic_kind": "entity",
            "semantic_type": "payments:policy",
            "consumer_namespace": "payments",
            "contract_version": "1.0",
            "contract_fingerprint": "cecf:v1:sha256:" + "0" * 64,
        },
        "properties": {"policy_code": "P1"},
        "rationale": "Consumer-qualified meaning.",
    }
    relationship = {
        "id": UUID,
        "alias_id": "PAYREL-0001",
        "alias_name": "payment-dependency",
        "relationship_type": "payments:depends_on",
        "qualification": {
            "semantic_kind": "relationship",
            "semantic_type": "payments:depends_on",
            "consumer_namespace": "payments",
            "contract_version": "1.0",
            "contract_fingerprint": "cecf:v1:sha256:" + "1" * 64,
        },
        "from_entity_id": UUID,
        "to_entity_id": UUID2,
        "properties": {"reason": "required"},
        "rationale": "Consumer-qualified relationship.",
    }
    validator = _authoring_validator("adr-logical.schema.json")
    root = _root(
        adr_type="logical",
        alias_id="ADR-L-0001",
        context="context",
        decisions=[_decision()],
        extension_entities=[entity],
        extension_relationships=[relationship],
    )
    assert not list(validator.iter_errors(root))
    assert _custom_qualification_is_exact(entity, "entity_type", entity["qualification"])
    assert _custom_qualification_is_exact(
        relationship, "relationship_type", relationship["qualification"]
    )

    for field, replacement in (
        ("semantic_type", "other:requirement"),
        ("consumer_namespace", "other"),
    ):
        invalid_entity = json.loads(json.dumps(root))
        invalid_entity["extension_entities"][0]["qualification"][field] = replacement
        assert list(validator.iter_errors(invalid_entity)) == []
        assert not _custom_qualification_is_exact(
            invalid_entity["extension_entities"][0],
            "entity_type",
            invalid_entity["extension_entities"][0]["qualification"],
        )

    invalid_relationship = json.loads(json.dumps(root))
    invalid_relationship["extension_relationships"][0]["qualification"][
        "semantic_type"
    ] = "other:requires"
    assert not list(validator.iter_errors(invalid_relationship))
    assert not _custom_qualification_is_exact(
        invalid_relationship["extension_relationships"][0],
        "relationship_type",
        invalid_relationship["extension_relationships"][0]["qualification"],
    )


def _normalized_custom_entity() -> dict[str, Any]:
    return {
        "id": UUID,
        "alias_id": "PAY-0001",
        "alias_name": "payment-policy",
        "alias_ref": "PAY-0001:payment-policy",
        "entity_type": "payments:policy",
        "name": "Payment policy",
        "summary": "Payment policy",
        "uri": "adr://payment-policy",
        "created_at": "2026-09-15T00:00:00Z",
        "entity_fingerprint": "sha256:" + "0" * 64,
        "lifecycle_stage": "active",
        "canonical_source": {},
        "completeness": {},
        "provenance": {},
        "extension": {
            "qualification": {
                "semantic_kind": "entity",
                "semantic_type": "payments:policy",
                "consumer_namespace": "payments",
                "contract_version": "1.0",
                "contract_fingerprint": "cecf:v1:sha256:" + "0" * 64,
            },
            "properties": {"policy_code": "P1"},
            "rationale": "Consumer-qualified meaning.",
        },
    }


def _normalized_custom_relationship() -> dict[str, Any]:
    return {
        "record_kind": "canonical",
        "id": UUID,
        "alias_id": "PAYREL-0001",
        "alias_name": "payment-dependency",
        "relationship_type": "payments:depends_on",
        "from_entity_id": UUID,
        "to_entity_id": UUID2,
        "canonical_source_ref": "source#relationship",
        "custom_qualification": {
            "semantic_kind": "relationship",
            "semantic_type": "payments:depends_on",
            "consumer_namespace": "payments",
            "contract_version": "1.0",
            "contract_fingerprint": "cecf:v1:sha256:" + "1" * 64,
        },
        "properties": {"reason": "required"},
        "rationale": "Consumer-qualified relationship.",
    }


def test_normalized_custom_qualification_and_properties_are_exact() -> None:
    entity_validator = _normalized_validator("normalized-entity.schema.json")
    entity = _normalized_custom_entity()
    assert not list(entity_validator.iter_errors(entity))
    assert _custom_qualification_is_exact(
        entity, "entity_type", entity["extension"]["qualification"]
    )
    mismatched_type = json.loads(json.dumps(entity))
    mismatched_type["extension"]["qualification"]["semantic_type"] = "other:requirement"
    assert list(entity_validator.iter_errors(mismatched_type)) == []
    assert not _custom_qualification_is_exact(
        mismatched_type, "entity_type", mismatched_type["extension"]["qualification"]
    )
    mismatched_namespace = json.loads(json.dumps(entity))
    mismatched_namespace["extension"]["qualification"]["consumer_namespace"] = "other"
    assert list(entity_validator.iter_errors(mismatched_namespace)) == []
    assert not _custom_qualification_is_exact(
        mismatched_namespace,
        "entity_type",
        mismatched_namespace["extension"]["qualification"],
    )

    relationship_validator = _normalized_validator("relationship-record.schema.json")
    relationship = _normalized_custom_relationship()
    assert not list(relationship_validator.iter_errors(relationship))
    assert _custom_qualification_is_exact(
        relationship, "relationship_type", relationship["custom_qualification"]
    )
    mismatched_relationship = json.loads(json.dumps(relationship))
    mismatched_relationship["custom_qualification"]["semantic_type"] = "other:requires"
    assert list(relationship_validator.iter_errors(mismatched_relationship)) == []
    assert not _custom_qualification_is_exact(
        mismatched_relationship,
        "relationship_type",
        mismatched_relationship["custom_qualification"],
    )
    nested = json.loads(json.dumps(entity))
    nested["extension"]["properties"] = {"nested": {"not": "allowed"}}
    assert list(entity_validator.iter_errors(nested))
    relationship_nested = json.loads(json.dumps(relationship))
    relationship_nested["properties"] = {"nested": {"not": "allowed"}}
    assert list(relationship_validator.iter_errors(relationship_nested))


def test_normalized_first_class_entities_require_typed_semantics() -> None:
    validator = _normalized_validator("normalized-entity.schema.json")
    base = {
        "id": UUID,
        "alias_id": "BOUND-0001",
        "alias_name": "sample-boundary",
        "alias_ref": "BOUND-0001:sample-boundary",
        "name": "Sample",
        "summary": "Sample",
        "uri": "adr://sample",
        "created_at": "2026-09-15T00:00:00Z",
        "entity_fingerprint": "sha256:" + "0" * 64,
        "lifecycle_stage": "active",
        "canonical_source": {},
        "completeness": {},
        "provenance": {},
    }
    boundary = {**base, "entity_type": "system_boundary", "description": "External edge."}
    boundary["external_dependencies"] = ["payments"]
    boundary["exposed_interfaces"] = [UUID2]
    assert not list(validator.iter_errors(boundary))
    assert list(validator.iter_errors({**base, "entity_type": "system_boundary"}))

    data_flow = {
        **base,
        "entity_type": "data_flow",
        "description": "Moves payment data.",
        "path": ["TOPO-API", "TOPO-DB"],
        "path_semantics": "owner_local_ordered_topology_path",
        "data_type": "payment",
        "volume": "1k/min",
        "latency_requirements": "p95 < 100ms",
    }
    assert not list(validator.iter_errors(data_flow))
    assert list(validator.iter_errors({**data_flow, "path_semantics": "not-a-path"}))

    evidence = {
        **base,
        "entity_type": "evidence_expectation",
        "evidence_kind": "test-result",
        "description": "A passing test.",
        "related_entity_ids": [UUID2],
    }
    assert not list(validator.iter_errors(evidence))
    missing_evidence_kind = dict(evidence)
    missing_evidence_kind.pop("evidence_kind")
    assert list(validator.iter_errors(missing_evidence_kind))


def test_normalized_v24_preserves_first_class_np_and_relationship_modes() -> None:
    entity = {
        "id": UUID,
        "alias_id": "FLOW-0001",
        "alias_name": "sample-flow",
        "alias_ref": "FLOW-0001:sample-flow",
        "entity_type": "data_flow",
        "name": "Flow",
        "summary": "Flow",
        "description": "Flow description",
        "uri": "adr://flow",
        "created_at": "2026-09-15T00:00:00Z",
        "entity_fingerprint": "sha256:" + "0" * 64,
        "lifecycle_stage": "active",
        "path": ["TOPO-API", "TOPO-DB"],
        "path_semantics": "owner_local_ordered_topology_path",
        "data_type": "payment",
        "volume": "1k/min",
        "latency_requirements": "p95 < 100ms",
        "canonical_source": {},
        "completeness": {},
        "provenance": {},
    }
    np = {
        "id": UUID2,
        "alias_id": "NP-0001",
        "alias_name": "sample-np",
        "alias_ref": "NP-0001:sample-np",
        "entity_type": "normative_proposition",
        "name": "MUST",
        "summary": "MUST",
        "uri": "adr://np",
        "created_at": "2026-09-15T00:00:00Z",
        "entity_fingerprint": "sha256:" + "1" * 64,
        "statement": "MUST",
        "normative_force": "MUST",
        "scope": "global",
        "declaring_adr": {
            "provider": "adr-kit",
            "id": UUID,
            "alias_id": "ADR-L-0001",
            "alias_name": "sample-adr",
        },
        "source_artifact": {
            "source_type": "authoring",
            "source_ref": "ADR-L-0001",
            "artifact_path": "adrs/logical/sample.yaml",
            "content_digest": "sha256:" + "2" * 64,
        },
        "source_contract": {
            "family": "authoring",
            "version": "1.7",
            "fingerprint": "sha256:" + "3" * 64,
        },
        "canonical_source": {},
        "completeness": {},
        "provenance": {},
    }
    document = {
        "schema_version": "2.4",
        "type": "normalized_entity_registry",
        "entities": [entity, np],
    }
    paths = list(NORMALIZED.glob("*.json"))
    store = {p.resolve().as_uri(): _document(p) for p in paths}
    store.update({_document(p)["$id"]: _document(p) for p in paths})
    schema_path = NORMALIZED / "normalized-entity-registry.schema.json"
    validator = Draft7Validator(
        _document(schema_path),
        resolver=RefResolver(schema_path.resolve().as_uri(), _document(schema_path), store=store),
    )
    assert not list(validator.iter_errors(document))

    canonical = {
        "record_kind": "canonical",
        "id": UUID,
        "alias_id": "EXT-0001",
        "alias_name": "custom-edge",
        "relationship_type": "payments:depends_on",
        "from_entity_id": UUID,
        "to_entity_id": UUID2,
        "canonical_source_ref": "source#relationship",
        "custom_qualification": {
            "semantic_kind": "relationship",
            "semantic_type": "payments:depends_on",
            "consumer_namespace": "payments",
            "contract_version": "1.0",
            "contract_fingerprint": "cecf:v1:sha256:" + "2" * 64,
        },
        "properties": {"reason": "required"},
        "rationale": "Consumer-qualified relationship.",
    }
    compatibility = {
        "record_kind": "compatibility",
        "relationship_id": "hash-not-canonical",
        "assertion_id": "asrt-" + "3" * 64,
        "relationship_type": "calls",
        "from_entity_id": UUID,
        "to_entity_id": UUID2,
        "provenance_classification": "explicit",
        "canonical_source_ref": "source#topology",
        "source_provenance": {
            "source_contract": "authoring@1.7",
            "source_pointer": "/component_topology/relationships/0",
        },
    }
    relationship_path = NORMALIZED / "relationship-record.schema.json"
    relationship_schema = _document(relationship_path)
    relationship_validator = Draft7Validator(
        relationship_schema,
        resolver=RefResolver(
            relationship_path.resolve().as_uri(), relationship_schema, store=store
        ),
    )
    assert not list(relationship_validator.iter_errors(canonical))
    assert not list(relationship_validator.iter_errors(compatibility))


def test_interpretation_covers_all_forward_types_and_resource_digests() -> None:
    contract = _document(INTERPRETATION / "contract.json")
    source_decoding = _document(INTERPRETATION / "resources" / "source-decoding-1.7.json")
    dispositions = {
        *(f"adr/{item}" for item in source_decoding["forward_authorable"]["adr"]),
        *(f"entity/{item}" for item in source_decoding["forward_authorable"]["entity"]),
        *(f"relationship/{item}" for item in source_decoding["forward_authorable"]["relationship"]),
        *(f"value/{item}" for item in source_decoding["forward_authorable"]["value"]),
    }
    assert len(dispositions) == 27
    assert {
        "entity/system_boundary",
        "entity/data_flow",
        "entity/evidence_expectation",
        "relationship/extension",
    } <= dispositions
    assert _document(INTERPRETATION / "resources" / "rules.json")["public_boundary"] == {
        "advertised": False,
        "execution": "not_implemented",
        "selected_by_current_semantic_contract_set": False,
    }
    for item in contract["resourceManifest"]:
        filename = item["canonicalResourceKey"].rsplit("/", 1)[-1] + ".json"
        value = _document(INTERPRETATION / "resources" / filename)
        digest = "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()
        assert digest == item["contentDigest"]


def test_normalized_v24_preserves_the_v23_np_contract() -> None:
    v23 = _document(ROOT / "schema" / "normalized-model" / "v2.3" / "normalized-entity.schema.json")
    v24 = _document(NORMALIZED / "normalized-entity.schema.json")
    v23_np = next(item for item in v23["oneOf"] if item["title"] == "Normative proposition")
    v24_np = next(
        item for item in v24["oneOf"] if item["title"] == "Lifecycle-free normative proposition"
    )
    assert set(v24_np["required"]) >= set(v23_np["required"])
    for field in ("declaring_adr", "source_artifact", "source_contract"):
        assert v24_np["properties"][field]["type"] == "object"
        assert v24_np["properties"][field]["additionalProperties"] is False
        assert set(v24_np["properties"][field]["required"]) == set(
            v23_np["properties"][field]["required"]
        )
    forbidden = {
        "lifecycle_stage",
        "applicability",
        "materiality",
        "authority_competence",
        "effectivity",
        "implementation_attribution",
    }
    assert not forbidden.intersection(v24_np["properties"])
    np = {
        "id": UUID,
        "alias_id": "NP-0001",
        "alias_name": "sample-np",
        "alias_ref": "NP-0001:sample-np",
        "entity_type": "normative_proposition",
        "name": "MUST",
        "summary": "MUST",
        "uri": "adr://np",
        "created_at": "2026-09-15T00:00:00Z",
        "entity_fingerprint": "sha256:" + "1" * 64,
        "statement": "MUST",
        "normative_force": "MUST",
        "scope": "global",
        "declaring_adr": {
            "provider": "adr-kit",
            "id": UUID,
            "alias_id": "ADR-L-0001",
            "alias_name": "sample-adr",
        },
        "source_artifact": {
            "source_type": "authoring",
            "source_ref": "ADR-L-0001",
            "artifact_path": "sample.yaml",
            "content_digest": "sha256:" + "2" * 64,
        },
        "source_contract": {
            "family": "authoring",
            "version": "1.7",
            "fingerprint": "sha256:" + "3" * 64,
        },
        "canonical_source": {},
        "completeness": {},
        "provenance": {},
    }
    validator = _normalized_validator("normalized-entity.schema.json")
    assert not list(validator.iter_errors(np))
    for field in forbidden:
        invalid = json.loads(json.dumps(np))
        invalid[field] = "forbidden"
        assert list(validator.iter_errors(invalid))


def test_architecture_interpretation_11_uses_canonical_scf_and_verified_closure() -> None:
    contract = _document(INTERPRETATION / "contract.json")
    schema = _document(INTERPRETATION / "schema.json")
    assert not list(Draft202012Validator(schema).iter_errors(contract))
    assert set(contract) == {
        "semanticContractFamily",
        "semanticContractVersion",
        "fingerprintScheme",
        "resourceManifest",
        "frozenNormativeConformanceResources",
        "semanticContractFingerprint",
    }
    calculated = calculate_semantic_contract_fingerprint(contract)
    assert calculated.success is True
    assert calculated.semantic_contract_fingerprint == contract["semanticContractFingerprint"]
    assert verify_semantic_contract(contract).success is True

    resources = []
    for entry in contract["resourceManifest"]:
        filename = entry["canonicalResourceKey"].rsplit("/", 1)[-1] + ".json"
        resources.append(
            {
                "canonicalResourceKey": entry["canonicalResourceKey"],
                "content": _document(INTERPRETATION / "resources" / filename),
            }
        )
    closure = validate_semantic_resource_closure(contract, resources)
    assert closure.success is True
    assert closure.closure_valid is True
    drifted = list(resources)
    drifted[0] = {**drifted[0], "content": {"resource": "drifted"}}
    drift = validate_semantic_resource_closure(contract, drifted)
    assert drift.success is False
    assert any(
        item.code == "semantic_contract.resource_digest_mismatch" for item in drift.diagnostics
    )

    rules = _document(INTERPRETATION / "resources" / "rules.json")
    assert rules["identity"]["custom_entity"] == "canonical_uuidv7"
    assert rules["identity"]["custom_relationship"] == "canonical_uuidv7"
    assert rules["identity"]["qualification_is_identity"] is False
    assert "entity_type=qualification.semantic_type" in rules["custom"]["entity_equalities"]
    assert (
        "namespace_prefix(entity_type)=qualification.consumer_namespace"
        in rules["custom"]["entity_equalities"]
    )
    assert (
        "relationship_type=qualification.semantic_type"
        in rules["custom"]["relationship_equalities"]
    )


def test_interpretation_conformance_is_vector_data_not_a_case_catalog() -> None:
    resource = _document(INTERPRETATION / "resources" / "conformance.json")
    cases = resource["cases"]
    assert [case["id"] for case in cases] == [f"I{index:02d}" for index in range(1, 39)]
    case_schema = resource["case_schema"]
    assert set(case_schema["dispositions"]) == {
        "accepted",
        "unresolved",
        "rejected",
        "historical_compatibility",
    }
    assert set(case_schema["basis_kinds"]) == {
        "authoring_document",
        "authoring_fragment",
        "topology_resolution",
        "composition_context",
        "endpoint_classification",
        "forward_type_disposition",
        "historical_compatibility",
        "absence_semantics",
    }

    root_schemas = {
        "I01": "adr-logical.schema.json",
        "I09": "adr-physical-system.schema.json",
        "I21": "adr-physical-component.schema.json",
    }
    topology_relationship_schema = (
        "adr-physical-system.schema.json"
        "#/properties/component_topology/properties/relationships/items"
    )
    topology_component_schema = (
        "adr-physical-system.schema.json"
        "#/properties/component_topology/properties/components/items"
    )

    for case in cases:
        assert {"id", "name", "source_contract", "input", "expected"} <= set(case)
        source_contract = case["source_contract"]
        assert source_contract["family"] == "authoring"
        assert source_contract["qualification"]
        assert {"source_pointer", "fragment", "basis"} <= set(case["input"])
        assert case["input"]["source_pointer"]
        basis = case["input"]["basis"]
        assert basis["kind"] in case_schema["basis_kinds"]
        expected = case["expected"]
        disposition = expected["disposition"]
        assert disposition in case_schema["dispositions"]
        if disposition in {"accepted", "unresolved"}:
            assert {"normalized_type", "identity", "fields"} <= set(expected)
            assert expected["fields"]
        elif expected["disposition"] == "rejected":
            assert {"reason_code", "reason"} <= set(expected)
        else:
            assert disposition == "historical_compatibility"
            assert expected["fields"]["forward_authority"] is False

        if basis["kind"] == "authoring_document":
            assert root_schemas[case["id"]] == basis["schema"]
            assert not list(
                _authoring_validator(basis["schema"]).iter_errors(case["input"]["fragment"])
            )
        elif basis["kind"] == "authoring_fragment":
            validator = _authoring_definition_validator(basis["schema"])
            fragment = case["input"]["fragment"]
            if case["id"] == "I31":
                valid = json.loads(json.dumps(fragment))
                valid["qualification"]["contract_fingerprint"] = "cecf:v1:sha256:" + "0" * 64
                assert not list(validator.iter_errors(valid))
                errors = list(validator.iter_errors(fragment))
                assert errors
                assert all(list(error.absolute_path)[:1] == ["qualification"] for error in errors)
                assert any("contract_fingerprint" in error.message for error in errors)
            elif case["id"] == "I32":
                valid = json.loads(json.dumps(fragment))
                valid.pop("lifecycle_stage")
                assert not list(validator.iter_errors(valid))
                errors = list(validator.iter_errors(fragment))
                assert errors
                assert any("lifecycle_stage" in error.message for error in errors)
            else:
                assert not list(validator.iter_errors(fragment))

        if basis["kind"] == "endpoint_classification":
            assert not list(
                _authoring_definition_validator(
                    "adr-common.schema.json#/definitions/custom_relationship"
                ).iter_errors(case["input"]["fragment"])
            )

        if basis["kind"] in {"topology_resolution", "composition_context"}:
            component_validator = _authoring_definition_validator(topology_component_schema)
            for component in basis["components"]:
                assert not list(component_validator.iter_errors(component))
            if basis["kind"] == "topology_resolution":
                relationship = json.loads(json.dumps(case["input"]["fragment"]))
                if case["id"] == "I34":
                    valid_relationship = json.loads(json.dumps(relationship))
                    valid_relationship["type"] = "calls"
                    assert not list(
                        _authoring_definition_validator(topology_relationship_schema).iter_errors(
                            valid_relationship
                        )
                    )
                    assert list(
                        _authoring_definition_validator(topology_relationship_schema).iter_errors(
                            relationship
                        )
                    )
                else:
                    assert not list(
                        _authoring_definition_validator(topology_relationship_schema).iter_errors(
                            relationship
                        )
                    )
                mapping = {
                    component["topology_key"]: component["component_ref"]
                    for component in basis["components"]
                }
                if disposition in {"accepted", "unresolved"} and case["id"] != "I30":
                    assert expected["fields"]["from_entity_id"] == mapping[relationship["from_key"]]
                    assert expected["fields"]["to_entity_id"] == mapping[relationship["to_key"]]
                if case["id"] == "I30":
                    assert "TOPO-MISSING" not in mapping
                    assert mapping["TOPO-DB"] == UUID2
                    assert expected["fields"]["source_pointer"] == case["input"]["source_pointer"]
                    assert expected["fields"]["missing_keys"] == ["TOPO-MISSING"]
                if case["id"] == "I34":
                    assert expected["reason_code"] == "forward_relationship_forbidden"

        if "endpoint_entities" in basis:
            endpoints = {endpoint["id"]: endpoint for endpoint in basis["endpoint_entities"]}
            fragment = case["input"]["fragment"]
            assert {fragment["from_entity_id"], fragment["to_entity_id"]} <= set(endpoints)
            assert {
                endpoints[fragment["from_entity_id"]]["classification"],
                endpoints[fragment["to_entity_id"]]["classification"],
            } <= {
                "canonical",
                "qualified_custom",
            }

        fragment = case["input"]["fragment"]
        if disposition == "accepted" and "entity_type" in fragment and "qualification" in fragment:
            assert _custom_qualification_is_exact(
                fragment, "entity_type", fragment["qualification"]
            )
        if (
            disposition == "accepted"
            and "relationship_type" in fragment
            and "qualification" in fragment
        ):
            assert _custom_qualification_is_exact(
                fragment, "relationship_type", fragment["qualification"]
            )

        if case["id"] == "I33":
            decoding = _document(INTERPRETATION / "resources" / "source-decoding-1.7.json")
            assert basis["forbidden_type"] in decoding["forward_forbidden"]
            assert case["input"]["fragment"]["entity_type"] == basis["forbidden_type"]
        if case["id"] == "I35":
            assert source_contract["version"] == "1.5/1.6"
            assert basis["historical_resources"]
        if case["id"] == "I38":
            assert case["input"]["fragment"] == {
                "absent": "no-declaration",
                "present_empty": [],
                "present_populated": [{"id": UUID}],
            }

    data_flow = next(case for case in cases if case["id"] == "I20")["expected"]
    data_flow_entity = {
        "id": UUID,
        "alias_id": "FLOW-0001",
        "alias_name": "sample-flow",
        "alias_ref": "FLOW-0001:sample-flow",
        "entity_type": data_flow["normalized_type"],
        "name": data_flow["fields"]["name"],
        "summary": data_flow["fields"]["description"],
        "uri": "adr://flow",
        "created_at": "2026-09-15T00:00:00Z",
        "entity_fingerprint": "sha256:" + "0" * 64,
        "lifecycle_stage": "active",
        "description": data_flow["fields"]["description"],
        "path": data_flow["fields"]["path"],
        "path_semantics": data_flow["fields"]["path_semantics"],
        "data_type": data_flow["fields"]["data_type"],
        "volume": data_flow["fields"]["volume"],
        "latency_requirements": data_flow["fields"]["latency_requirements"],
        "canonical_source": {},
        "completeness": {},
        "provenance": {},
    }
    assert not list(
        _normalized_validator("normalized-entity.schema.json").iter_errors(data_flow_entity)
    )

    for case_id in ("I10", "I25"):
        case = next(item for item in cases if item["id"] == case_id)
        fields = case["expected"]["fields"]
        entity = {
            **data_flow_entity,
            "alias_id": "SYSBOUND-0001" if case_id == "I10" else "EVID-0001",
            "alias_name": "sample-boundary" if case_id == "I10" else "sample-evidence",
            "entity_type": case["expected"]["normalized_type"],
            "name": fields.get("name", "Expected evidence"),
            "summary": fields["description"],
            **fields,
        }
        if case_id == "I25":
            entity["description"] = fields["description"]
        assert not list(_normalized_validator("normalized-entity.schema.json").iter_errors(entity))

    relationship_validator = _normalized_validator("relationship-record.schema.json")
    for case_id in ("I27", "I28", "I29", "I36"):
        case = next(item for item in cases if item["id"] == case_id)
        relationship = _normalized_custom_relationship()
        relationship["alias_id"] = case["input"]["fragment"]["alias_id"]
        relationship["alias_name"] = case["input"]["fragment"]["alias_name"]
        relationship.update(
            {
                key: value
                for key, value in case["expected"]["fields"].items()
                if key in {"relationship_type", "from_entity_id", "to_entity_id", "properties"}
            }
        )
        assert not list(relationship_validator.iter_errors(relationship))

    for case_id in ("I12", "I13", "I14", "I15", "I16", "I17", "I18", "I19", "I37"):
        case = next(item for item in cases if item["id"] == case_id)
        fragment = case["input"]["fragment"]
        relationship_type = (
            case["expected"]["fields"].get("relationship_type")
            or case["expected"]["normalized_type"]
        )
        if case_id == "I19":
            relationship_type = "composed_of"
            from_id = fragment["system_id"]
            to_id = fragment["components"][0]["component_ref"]
        else:
            from_id = case["expected"]["fields"]["from_entity_id"]
            to_id = case["expected"]["fields"]["to_entity_id"]
        compatibility = {
            "record_kind": "compatibility",
            "relationship_id": f"compatibility:{case_id}",
            "assertion_id": "asrt-" + "2" * 64,
            "relationship_type": relationship_type,
            "from_entity_id": from_id,
            "to_entity_id": to_id,
            "provenance_classification": "explicit",
            "evidence": [],
            "canonical_source_ref": f"conformance/{case_id}",
            "source_provenance": {
                "source_contract": "authoring@1.7",
                "source_pointer": case["input"]["source_pointer"],
                "topology_key_endpoints": {
                    "from_key": fragment.get("from_key", "TOPO-API"),
                    "to_key": fragment.get("to_key", "TOPO-DB"),
                },
            },
        }
        assert not list(relationship_validator.iter_errors(compatibility))
        assert compatibility["record_kind"] == "compatibility"
        assert list(
            relationship_validator.iter_errors(
                {**compatibility, "record_kind": "canonical", "id": UUID}
            )
        )
