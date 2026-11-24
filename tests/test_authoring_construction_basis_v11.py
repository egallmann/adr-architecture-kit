"""Keep ACC 1.1 candidate authority while rejecting its retired public route."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adr_kit.core import execute_validated_semantic_core_request, supports_semantic_core_operation

pytestmark = pytest.mark.fast

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "contracts" / "semantic-core" / "v1.5" / "contract.json"
OPERATION = "prepare_authoring_construction_basis_1_1"


def test_candidate_contract_is_preserved_but_protocol_15_is_not_routable() -> None:
    contract = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    envelope = contract["$defs"]["request_envelope"]["properties"]
    assert envelope["core_contract_version"]["const"] == "1.5"
    assert envelope["operation"]["const"] == OPERATION
    assert not supports_semantic_core_operation("1.5", OPERATION)

    result = execute_validated_semantic_core_request(
        {"core_contract_version": "1.5", "operation": OPERATION}
    )
    assert result["core_contract_version"] == "1.0"
    assert result["outcome"] == "invalid_request"
    assert result["diagnostics"][0]["code"] == "core.invalid_request"
    assert result["diagnostics"][0]["message"] == "unsupported core_contract_version"
