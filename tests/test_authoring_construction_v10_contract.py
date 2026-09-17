"""Executable contract-level conformance for Authoring Construction Contract 1.0."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import rfc8785
from jsonschema import Draft202012Validator

from adr_kit.semantic_contract import (
    calculate_semantic_contract_fingerprint,
    validate_semantic_resource_closure,
    verify_semantic_contract,
)

ROOT = Path(__file__).resolve().parents[1]
ACC = ROOT / "contracts" / "authoring-construction" / "v1.0"


def _document(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_acc_contract_schema_and_document_are_strictly_valid() -> None:
    schema = _document(ACC / "schema.json")
    contract = _document(ACC / "contract.json")
    Draft202012Validator.check_schema(schema)
    assert not list(Draft202012Validator(schema).iter_errors(contract))
    assert set(contract) == {
        "semanticContractFamily",
        "semanticContractVersion",
        "fingerprintScheme",
        "resourceManifest",
        "frozenNormativeConformanceResources",
        "semanticContractFingerprint",
    }


def test_acc_scf_and_resource_closure_are_verified_by_shared_authority() -> None:
    contract = _document(ACC / "contract.json")
    assert verify_semantic_contract(contract).success is True
    calculated = calculate_semantic_contract_fingerprint(contract)
    assert calculated.success is True
    assert calculated.semantic_contract_fingerprint == contract["semanticContractFingerprint"]

    resources = [
        {
            "canonicalResourceKey": entry["canonicalResourceKey"],
            "content": _document(
                ACC / "resources" / f"{entry['canonicalResourceKey'].split('/')[-1]}.json"
            ),
        }
        for entry in contract["resourceManifest"]
    ]
    closure = validate_semantic_resource_closure(contract, resources)
    assert closure.success is True
    assert closure.closure_valid is True

    for entry, supplied in zip(contract["resourceManifest"], resources, strict=True):
        digest = "sha256:" + hashlib.sha256(rfc8785.dumps(supplied["content"])).hexdigest()
        assert entry["contentDigest"] == digest


def test_acc_corpus_has_frozen_self_contained_cases_and_exact_outcomes() -> None:
    corpus = _document(ACC / "resources" / "conformance.json")
    cases = corpus["cases"]
    assert [case["id"] for case in cases] == [f"C{index:02d}" for index in range(1, 41)]
    assert corpus["case_schema"]["outcomes"] == [
        "Constructed",
        "Rejected",
        "Unavailable",
        "Unresolved",
    ]
    assert {case["operation"] for case in cases} == {
        "validate_authoring",
        "construct_authoring_set",
    }
    assert all({"request", "exact_basis"} <= set(case["input"]) for case in cases)
    assert all({"outcome", "diagnostics"} <= set(case["expected"]) for case in cases)
    assert {case["expected"]["outcome"] for case in cases} == {
        "Constructed",
        "Rejected",
        "Unavailable",
        "Unresolved",
    }


def test_acc_corpus_covers_blocked_checks_and_detached_constructed_result() -> None:
    cases = _document(ACC / "resources" / "conformance.json")["cases"]
    by_id = {case["id"]: case for case in cases}
    assert any(item["status"] == "blocked" for item in by_id["C25"]["expected"]["diagnostics"])
    assert by_id["C32"]["expected"]["outcome"] == "Rejected"
    assert by_id["C33"]["expected"]["outcome"] == "Unavailable"
    assert by_id["C35"]["expected"]["round_trip"] == "semantic_equivalent"
    assert "construction_map" in by_id["C36"]["expected"]["result_contains"]
    assert "candidate_source_basis" in by_id["C37"]["expected"]["result_contains"]
    assert by_id["C38"]["expected"]["side_effects"]["repository"] is False


def test_acc_policy_resource_preserves_authority_ceiling_and_boundaries() -> None:
    rules = _document(ACC / "resources" / "rules.json")
    assert rules["outcomes"]["exact"] == [
        "Constructed",
        "Rejected",
        "Unavailable",
        "Unresolved",
    ]
    assert rules["outcomes"]["Constructed"]["partial"] is False
    assert rules["relationships"]["properties_imply_edges"] is False
    assert rules["relationships"]["forbidden"] == ["consumes_interface", "composed_of"]
    assert rules["identity"]["forbidden_derivations"] == [
        "alias",
        "prose",
        "path",
        "source_location",
        "content_hash",
        "source_order",
        "array_order",
        "composition_position",
    ]
    assert rules["detached_result"]["side_effects"] == {
        "repository": False,
        "git": False,
        "runtime": False,
        "runtime_snapshot": False,
        "admission": False,
        "alias_reservation": False,
    }
