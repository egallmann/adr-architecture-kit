"""Contract and boundary checks for the closed successor materialization transport."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "semantic-core" / "v1.3" / "contract.json"


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _source_contract(version: str = "1.7") -> dict[str, Any]:
    return {
        "family": "authoring",
        "version": version,
        "schemaResource": {
            "canonicalResourceKey": f"authoring/{version}/schema/adr-logical.schema",
            "contentDigest": "sha256:" + "a" * 64,
        },
        "resourceClosure": [
            {
                "canonicalResourceKey": f"authoring/{version}/schema/adr-common.schema",
                "contentDigest": "sha256:" + "b" * 64,
            },
            {
                "canonicalResourceKey": f"authoring/{version}/schema/types.schema",
                "contentDigest": "sha256:" + "c" * 64,
            },
            {
                "canonicalResourceKey": f"authoring/{version}/schema/adr-logical.schema",
                "contentDigest": "sha256:" + "a" * 64,
            },
        ],
    }


def _request() -> dict[str, Any]:
    return {
        "core_contract_version": "1.3",
        "operation": "materialize_architecture",
        "request": {
            "operation": "materialize_architecture",
            "materializationContractVersion": "1.1",
            "semanticContractSetId": "scs:v1:sha256:" + "d" * 64,
            "authorityProvider": {"kind": "fixture-provider", "architectureNamespace": "example"},
            "sourceBasis": {
                "sealed": True,
                "providerSourceIdentity": "fixture-provider:example",
                "sourceRevision": "revision-1",
                "artifacts": [
                    {
                        "sourceRef": "ADR-L-0001",
                        "artifactPath": "architecture/ADR-L-0001.yaml",
                        "contentDigest": "sha256:" + "e" * 64,
                        "sourceContract": _source_contract(),
                        "document": {"schema_version": "1.7", "adr_type": "logical"},
                    }
                ],
            },
            "providerProvenance": {
                "semanticCoreContractVersion": "1.3",
                "packageVersion": "0.11.1",
                "hostBinding": "test",
            },
            "targetOperation": "materialize_architecture",
            "direction": "forward",
            "useMode": "new",
            "profile": {
                "profileFamily": "architecture-materialization",
                "profileVersion": "1.1",
                "profileId": "architecture-materialization@1.1",
                "participatingFamilies": [
                    {
                        "semanticContractFamily": "architecture-interpretation",
                        "semanticContractVersion": "1.1",
                        "cardinality": 1,
                    },
                    {
                        "semanticContractFamily": "normalized-model",
                        "semanticContractVersion": "2.4",
                        "cardinality": 1,
                    },
                    {
                        "semanticContractFamily": "normative-semantics",
                        "semanticContractVersion": "1.0",
                        "cardinality": 1,
                    },
                ],
                "operations": ["materialize_architecture"],
                "selectionPurposes": ["architecture-materialization"],
            },
            "definitions": [],
            "sets": [],
            "qualifications": [],
            "catalog": {},
            "policy": {},
        },
    }


def test_protocol_13_request_requires_exact_successor_source_binding() -> None:
    validator = Draft202012Validator(_contract())
    assert not list(validator.iter_errors(_request()))

    old = _request()
    old["request"]["sourceBasis"]["artifacts"][0]["sourceContract"] = _source_contract("1.6")
    assert list(validator.iter_errors(old))

    old_materialization = _request()
    old_materialization["request"]["materializationContractVersion"] = "1.0"
    assert list(validator.iter_errors(old_materialization))


def test_protocol_13_result_models_successor_materialization_without_internal_registries() -> None:
    result = {
        "core_contract_version": "1.3",
        "operation": "materialize_architecture",
        "result": {
            "operation": "materialize_architecture",
            "success": False,
            "outcome": "Unavailable",
            "materializationContractVersion": "1.1",
            "authorityProvider": {"kind": "fixture-provider", "architectureNamespace": "example"},
            "sourceBasis": _request()["request"]["sourceBasis"],
            "sourceContractClosure": [_source_contract()],
            "semanticBasis": {
                "semanticContractSetId": "scs:v1:sha256:" + "d" * 64,
                "authorityStateFingerprint": None,
            },
            "normalizedModel": None,
            "sourceCapabilityLimitations": [],
            "providerProvenance": {
                "semanticCoreContractVersion": "1.3",
                "packageVersion": "0.11.1",
                "hostBinding": "test",
            },
            "diagnostics": [
                {"severity": "error", "code": "core.operation_unavailable", "message": "closed"}
            ],
        },
    }
    assert not list(Draft202012Validator(_contract()).iter_errors(result))
    assert "entityRegistry" not in result["result"]
    assert "relationshipRegistry" not in result["result"]


def test_python_protocol_mirror_is_canonical() -> None:
    mirror = ROOT / "src" / "adr_kit" / "core" / "semantic-core-contract-v1.3.json"
    assert json.loads(mirror.read_text(encoding="utf-8")) == _contract()
