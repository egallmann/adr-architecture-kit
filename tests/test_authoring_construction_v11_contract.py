"""Publication checks for the immutable, non-executable ACC 1.1 authority."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, RefResolver

from adr_kit.semantic_contract import (
    calculate_semantic_contract_fingerprint,
    get_semantic_contract,
    load_semantic_resource,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ACC11 = ROOT / "contracts" / "authoring-construction" / "v1.1"
ACC10 = ROOT / "contracts" / "authoring-construction" / "v1.0"
AI12 = ROOT / "contracts" / "architecture-interpretation" / "v1.2"
NM24 = ROOT / "schema" / "normalized-model" / "v2.4"
SEMANTIC = ROOT / "contracts" / "semantic-contract" / "v1.0"


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resource_path(root: Path, key: str) -> Path:
    parts = key.split("/")
    filename = key.replace("/", "-") + ".json"
    path = root / filename
    if not path.is_file() and len(parts) == 3:
        path = root / f"{parts[0]}-{parts[2]}.json"
    return path


def _schema_store(schema: dict[str, Any]) -> dict[str, Any]:
    store: dict[str, Any] = {schema["$id"]: schema}
    ledger = _read(ACC11 / "resources" / "ledger.schema.json")
    store[ledger["$id"]] = ledger
    store[
        "https://adr-kit.dev/semantic-contract/resources/authoring-construction/1.1/ledger.schema.json"
    ] = ledger
    for path in NM24.glob("*.json"):
        value = cast(dict[str, Any], _read(path))
        store[value["$id"]] = value
        store[
            "https://adr-kit.dev/semantic-contract/resources/normalized-model/2.4/schema/"
            + path.name
        ] = value
    return store


def test_acc11_is_independently_fingerprinted_and_exactly_discoverable() -> None:
    contract = cast(dict[str, Any], _read(ACC11 / "contract.json"))
    schema = cast(dict[str, Any], _read(ACC11 / "schema.json"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        schema,
        resolver=RefResolver(schema["$id"], schema, store=_schema_store(schema)),
    )
    assert not list(validator.iter_errors(contract))
    assert contract["semanticContractFamily"] == "authoring-construction"
    assert contract["semanticContractVersion"] == "1.1"
    assert (
        calculate_semantic_contract_fingerprint(contract).semantic_contract_fingerprint
        == contract["semanticContractFingerprint"]
    )
    assert verify_semantic_contract(contract).success is True
    exact = get_semantic_contract("authoring-construction", "1.1")
    historical = get_semantic_contract("authoring-construction", "1.0")
    assert exact.semantic_contract_fingerprint == contract["semanticContractFingerprint"]
    assert (
        historical.semantic_contract_fingerprint
        == "scf:v1:sha256:b94f67ebff64b6560206715cef87a49b4444b71aa661cce92a6c3d04d8bf2703"
    )
    resources = [
        {
            "canonicalResourceKey": item["canonicalResourceKey"],
            "content": load_semantic_resource(item["canonicalResourceKey"]),
        }
        for item in contract["resourceManifest"]
    ]
    closure = validate_semantic_resource_closure(contract, resources)
    assert closure.success is True
    assert closure.closure_valid is True
    assert contract["frozenNormativeConformanceResources"] == [
        "authoring-construction/1.1/conformance"
    ]


def test_acc11_binds_exact_ai12_and_full_immutable_dependency_closures() -> None:
    acc = _read(ACC11 / "contract.json")
    ai = _read(AI12 / "contract.json")
    rules = _read(ACC11 / "resources" / "rules.json")
    manifest = {item["canonicalResourceKey"]: item for item in acc["resourceManifest"]}
    assert (
        rules["authority"]["architecture_interpretation"]["fingerprint"]
        == ai["semanticContractFingerprint"]
    )
    assert rules["authority"]["architecture_interpretation"]["fingerprint"] == (
        "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a"
    )
    assert {entry["canonicalResourceKey"] for entry in ai["resourceManifest"]} <= set(manifest)
    assert "architecture-interpretation/1.2/contract" in manifest
    assert "authoring-domain/1.1/contract" in manifest
    assert "authoring-domain/1.1/schema" in manifest
    assert "authoring-construction/1.0/conformance" in manifest
    assert {
        "authoring/1.7/schema/adr-common.schema",
        "authoring/1.7/schema/adr-logical.schema",
        "authoring/1.7/schema/adr-physical-base.schema",
        "authoring/1.7/schema/adr-physical-component.schema",
        "authoring/1.7/schema/adr-physical-system.schema",
        "authoring/1.7/schema/types.schema",
        "custom-entity/1.0/contract",
        "normalized-model/2.4/schema/normalized-architecture-model.schema",
    } <= set(manifest)


def test_acc11_ledger_and_constructed_result_require_complete_nm24_evidence() -> None:
    schema = _read(ACC11 / "schema.json")
    defs = schema["$defs"]
    normalized_model = defs["normalized_result"]["properties"]["model"]
    assert normalized_model["$ref"] == (
        "../../normalized-model/2.4/schema/normalized-architecture-model.schema.json"
    )
    qualification = defs["construction_qualification"]
    assert set(qualification["required"]) == {
        "authority",
        "candidate_source_basis",
        "interpretation",
        "normalized_model",
        "expected_ledger",
        "observed_ledger",
        "comparison",
    }
    construct = defs["construction_result"]
    required = set(construct["allOf"][1]["required"])
    assert "construction_qualification" in required
    constructed = construct["allOf"][2]["then"]
    assert "construction_qualification" in constructed["required"]
    evidence = constructed["properties"]["construction_qualification"]["properties"]
    assert evidence["interpretation"]["properties"]["status"] == {"const": "complete"}
    assert evidence["normalized_model"]["properties"]["schema_validation"] == {"const": "valid"}
    assert evidence["comparison"]["properties"]["status"] == {"const": "semantic_equivalent"}
    assert evidence["comparison"]["properties"]["mismatches"] == {"maxItems": 0}
    ledger = _read(ACC11 / "resources" / "ledger.schema.json")
    assert set(ledger["required"]) == {
        "ledger_version",
        "semantic_units",
        "relationships",
        "unresolved",
    }
    assert ledger["$defs"]["semantic_unit"]["required"] == ["semantic_type", "identity", "fields"]
    assert ledger["$defs"]["relationship"]["properties"]["multiplicity"]["minimum"] == 1


def test_acc11_equivalence_and_outcome_policies_are_closed_and_fail_closed() -> None:
    rules = _read(ACC11 / "resources" / "rules.json")
    equivalence = rules["equivalence"]
    assert (
        equivalence["algorithm_id"]
        == "authoring-construction/1.1/complete-semantic-ledger-equality"
    )
    assert equivalence["inputs"] == ["complete_expected_ledger", "complete_observed_ledger"]
    assert (
        equivalence["field_key_authority"]
        == "architecture-interpretation/1.2/field-dispositions-1.7-to-2.4"
    )
    assert equivalence["authorized_difference_classes"] == [
        "canonical_field_placement",
        "compatibility_projection",
        "declared_absence",
        "deterministic_ceremony",
    ]
    assert (
        equivalence["direct_semantic_value"]
        == "direct typed semantic equality; it is not a difference class"
    )
    assert equivalence["provenance_substitution_for_missing_semantics"] is False
    assert equivalence["fingerprint_or_count_substitution_for_ledger_equality"] is False
    assert rules["outcomes"]["precedence"] == [
        "Rejected",
        "Unavailable",
        "Unresolved",
        "Constructed",
    ]
    assert rules["outcomes"]["blocked_is_success"] is False
    assert rules["outcomes"]["all_independent_diagnostics_retained"] is True
    assert rules["implementation_posture"]["public_execution_capability"] == "not_advertised"


def test_acc11_authority_conformance_is_frozen_and_does_not_claim_runtime_execution() -> None:
    conformance = _read(ACC11 / "resources" / "conformance.json")
    conformance_schema = _read(ACC11 / "resources" / "conformance.schema.json")
    Draft202012Validator.check_schema(conformance_schema)
    assert not list(Draft202012Validator(conformance_schema).iter_errors(conformance))
    cases = conformance["cases"]
    ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert len(cases) >= 26
    assert all(case["runtime_coverage"] == "authority_only_not_implemented" for case in cases)
    claims = "\n".join(case["claim"] for case in cases).lower()
    for required in (
        "standalone fragment",
        "mixed document",
        "c05",
        "c07",
        "absent exact ai 1.2 authority",
        "custom entity",
        "custom relationship",
        "topology",
        "composed_of",
        "multiplicity",
        "unresolved",
        "detached context",
        "source_semantics",
        "complete schema-valid",
        "acc1.0",
    ):
        assert required in claims
    c32 = next(case for case in cases if case["case_id"] == "ACC11-06")
    assert (
        c32["fixture"]["input"]["expected_ledger"]["semantic_units"][0]["fields"][0][
            "semantic_field_key"
        ]
        == "entity/gap#/context"
    )
    assert c32["fixture"]["input"]["observed_ledger"]["semantic_units"][0]["fields"] == []
    assert c32["assertions"][0] == {
        "path": "comparison.status",
        "operator": "equals",
        "expected": "semantic_mismatch",
    }


def test_acc11_publication_does_not_select_or_advertise_execution() -> None:
    rules = _read(ACC11 / "resources" / "rules.json")
    current = _read(SEMANTIC / "current" / "semantic-contract-current-1.0.json")
    set_path = SEMANTIC / "sets" / (current["semanticContractSetId"].replace(":", "-") + ".json")
    selected = _read(set_path)
    assert current["semanticContractSetId"] == (
        "scs:v1:sha256:d12ce535f0a90c23741dfa516d207091197c2772dbcd538fabb133bdf5b79af6"
    )
    assert not any(
        member["semanticContractFamily"] == "authoring-construction"
        and member["semanticContractVersion"] == "1.1"
        for member in selected["members"]
    )
    assert rules["publication_posture"] == {
        "status": "published_authority_only",
        "execution_capability_advertised": False,
        "execution_implemented": False,
        "current_semantic_contract_selection": False,
    }


def test_historical_authorities_and_corpus_remain_byte_stable() -> None:
    ai11 = _read(ROOT / "contracts" / "architecture-interpretation" / "v1.1" / "contract.json")
    ai12 = _read(AI12 / "contract.json")
    acc10 = _read(ACC10 / "contract.json")
    assert ai11["semanticContractFingerprint"] == (
        "scf:v1:sha256:3650db1f6763a1e7ab81a3f3663d002b3e97ffc0ae007bd7d3543508c069100e"
    )
    assert ai12["semanticContractFingerprint"] == (
        "scf:v1:sha256:2a9300b1d7bdc9a80421cb94294fbd2f345531b5147644d02ae4bcc5c436d75a"
    )
    assert acc10["semanticContractFingerprint"] == (
        "scf:v1:sha256:b94f67ebff64b6560206715cef87a49b4444b71aa661cce92a6c3d04d8bf2703"
    )
    assert hashlib.sha256((ACC10 / "resources" / "conformance.json").read_bytes()).hexdigest() == (
        "2b88de11e8d4cd8bea7e2c27a2edc781a20663a335cc38c6e2b4f29dd182df67"
    )
    assert (
        not (ACC11 / "resources" / "conformance.json").read_bytes()
        == (ACC10 / "resources" / "conformance.json").read_bytes()
    )
    assert Counter(
        case["id"] for case in _read(ACC10 / "resources" / "conformance.json")["cases"]
    ) == Counter({f"C{i:02}": 1 for i in range(1, 43)})


def test_acc11_bundled_mirrors_match_canonical_resources() -> None:
    contract = _read(ACC11 / "contract.json")
    canonical = SEMANTIC / "resources"
    bundled = ROOT / "src" / "adr_kit" / "semantic_contract" / "v1_0" / "resources"
    for entry in contract["resourceManifest"]:
        key = entry["canonicalResourceKey"]
        assert (
            _resource_path(canonical, key).read_bytes() == _resource_path(bundled, key).read_bytes()
        )
