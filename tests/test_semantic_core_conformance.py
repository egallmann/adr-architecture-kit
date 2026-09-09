from __future__ import annotations

import json
from pathlib import Path

from adr_kit.core import execute_semantic_core_request

VECTORS = Path("contracts/semantic-core/v1.0/vectors/contract-validation.json")
METADATA_VECTORS = Path("contracts/semantic-core/v1.0/vectors/project-metadata-validation.json")
LINKAGE_VECTORS = Path("contracts/semantic-core/v1.0/vectors/embodiment-linkage.json")
REPOSITORY_VECTORS = Path("contracts/semantic-core/v1.0/vectors/repository-validation.json")
ARTIFACT_VECTORS = Path(
    "contracts/semantic-core/v1.0/vectors/generated-artifact-classification.json"
)
REFERENCE_VECTORS = Path(
    "contracts/semantic-core/v1.0/vectors/architecture-reference-validation.json"
)
ARCHITECTURE_VECTORS = Path("contracts/semantic-core/v1.0/vectors/architecture-validation.json")
ATTRIBUTION_SHIM_VECTORS = Path(
    "contracts/semantic-core/v1.0/vectors/attribution-shim-generation.json"
)
SEMANTIC_CONTRACT_VECTORS = Path("contracts/semantic-core/v1.0/vectors/semantic-contract.json")


def test_python_binding_matches_shared_semantic_contract_vectors() -> None:
    document = json.loads(SEMANTIC_CONTRACT_VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        for field in (
            "canonical_preimage_json",
            "fingerprint",
            "semantic_contract_fingerprint",
            "semantic_contract_set_fingerprint",
        ):
            if field in expected:
                assert result[field] == expected[field], case["name"]
        if "diagnostic_codes" in expected:
            assert [item["code"] for item in result["diagnostics"]] == expected[
                "diagnostic_codes"
            ], case["name"]


def test_python_binding_matches_shared_semantic_core_vectors() -> None:
    document = json.loads(VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        assert result["outcome"] == expected["outcome"], case["name"]
        if "sentinel_field_count" in expected:
            assert result["sentinel_field_count"] == expected["sentinel_field_count"], case["name"]
        if "non_complete_entity_count" in expected:
            assert (
                result["non_complete_entity_count"] == expected["non_complete_entity_count"]
            ), case["name"]
        if "issue_count" in expected:
            assert len(result["issues"]) == expected["issue_count"], case["name"]
        if "issue_codes" in expected:
            assert [
                item["code"] for item in result["diagnostics"] if item["code"] != "contract.issue"
            ] == expected["issue_codes"], case["name"]


def test_python_binding_matches_shared_project_metadata_vectors() -> None:
    document = json.loads(METADATA_VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        assert len(result["diagnostics"]) == expected["diagnostic_count"], case["name"]
        if "paths" in expected:
            assert [item["path"] for item in result["diagnostics"]] == expected["paths"], case[
                "name"
            ]


def test_python_binding_matches_shared_linkage_vectors() -> None:
    document = json.loads(LINKAGE_VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        assert len(result["links"]) == expected["link_count"], case["name"]
        assert len(result["rejected_claims"]) == expected["rejected_count"], case["name"]
        assert result["error_count"] == expected["error_count"], case["name"]
        assert result["warning_count"] == expected["warning_count"], case["name"]


def test_python_binding_matches_shared_repository_vectors() -> None:
    document = json.loads(REPOSITORY_VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        assert len(result["diagnostics"]) == expected["diagnostic_count"], case["name"]
        assert result["entity_count"] == expected["entity_count"], case["name"]
        if "diagnostic_codes" in expected:
            assert [item["code"] for item in result["diagnostics"]] == expected[
                "diagnostic_codes"
            ], case["name"]


def test_python_binding_matches_shared_generated_artifact_vectors() -> None:
    document = json.loads(ARTIFACT_VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        assert result["status"] == expected["status"], case["name"]
        assert result["reason_code"] == expected["reason_code"], case["name"]


def test_python_binding_matches_shared_architecture_reference_vectors() -> None:
    document = json.loads(REFERENCE_VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        assert result["error_count"] == expected["error_count"], case["name"]
        assert result["warning_count"] == expected["warning_count"], case["name"]
        assert len(result["diagnostics"]) == expected["diagnostic_count"], case["name"]


def test_python_binding_matches_shared_architecture_validation_vectors() -> None:
    document = json.loads(ARCHITECTURE_VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        assert result["error_count"] == expected["error_count"], case["name"]
        assert result["warning_count"] == expected["warning_count"], case["name"]
        assert len(result["diagnostics"]) == expected["diagnostic_count"], case["name"]
        if "codes" in expected:
            assert [item["code"] for item in result["diagnostics"]] == expected["codes"], case[
                "name"
            ]


def test_python_binding_matches_shared_attribution_shim_vectors() -> None:
    from adr_kit.attribution_shim_generator import generate_shim

    document = json.loads(ATTRIBUTION_SHIM_VECTORS.read_text(encoding="utf-8"))
    for case in document["cases"]:
        result = execute_semantic_core_request(case["request"])
        expected = case["expected"]
        assert result["success"] is expected["success"], case["name"]
        assert result["language"] == expected["language"], case["name"]
        assert len(result["content"]) == expected["content_length"], case["name"]
        assert result["content"] == generate_shim(expected["language"]), case["name"]
