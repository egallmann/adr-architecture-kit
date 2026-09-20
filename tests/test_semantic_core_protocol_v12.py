"""Conformance for the additive semantic-core protocol 1.2 transport boundary."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from adr_kit.core import validate_semantic_core_protocol

# Reuse the existing verified ACC binding helper rather than defining a second
# self-binding implementation in this protocol test.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_authoring_construction_v10_contract import _verified_bound_conformance

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "contracts" / "semantic-core" / "v1.2"
ACC = ROOT / "contracts" / "authoring-construction" / "v1.0"


def _document(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _protocol_validator() -> Draft202012Validator:
    schema = _document(PROTOCOL / "contract.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _errors(validator: Draft202012Validator, value: Any) -> list[Any]:
    return list(validator.iter_errors(value))


def _acc_errors(schema: dict[str, Any], value: Any, definition: str) -> list[Any]:
    validator = Draft202012Validator(schema)
    return list(validator.descend(value, {"$ref": f"#/$defs/{definition}"}))


def _remove_path(value: dict[str, Any], path: list[str]) -> None:
    current: dict[str, Any] = value
    for part in path[:-1]:
        child = current[part]
        assert isinstance(child, dict)
        current = child
    del current[path[-1]]


def _envelope(case: dict[str, Any], kind: str, operation: str | None = None) -> dict[str, Any]:
    selected = case["input"] if kind == "request" else case["expected"]["result"]
    return {
        "core_contract_version": "1.2",
        "operation": operation or case["operation"],
        kind: deepcopy(selected),
    }


def _bound_cases() -> dict[str, dict[str, Any]]:
    acc_schema = _document(ACC / "schema.json")
    _, bound, _ = _verified_bound_conformance(acc_schema)
    return {case["id"]: case for case in bound["cases"]}


def test_v12_transport_vectors_cover_the_closed_envelope_surface() -> None:
    validator = _protocol_validator()
    vectors = _document(PROTOCOL / "vectors" / "authoring-construction-transport.json")
    cases = {case["id"]: case for case in vectors["cases"]}
    assert list(cases) == [f"T{index:02d}" for index in range(1, 13)]

    bound = _bound_cases()
    for case in cases.values():
        kind = case.get("kind")
        if kind in {"request", "result"}:
            envelope = _envelope(bound[case["source_case"]], kind, case["operation"])
            assert not _errors(validator, envelope), case["name"]
            validate_semantic_core_protocol(envelope)
            assert envelope[kind]["operation"] == envelope["operation"]
            continue

        if kind == "mismatch":
            envelope = _envelope(bound[case["source_case"]], "request", "construct_authoring_set")
            assert _errors(validator, envelope), case["name"]
            try:
                validate_semantic_core_protocol(envelope)
            except ValueError:
                pass
            else:
                raise AssertionError(case["name"])
            continue

        if kind == "wrong_version":
            envelope = _envelope(bound[case["source_case"]], "request", case["operation"])
            envelope["core_contract_version"] = "1.1"
            assert _errors(validator, envelope), case["name"]
            try:
                validate_semantic_core_protocol(envelope)
            except ValueError:
                pass
            else:
                raise AssertionError(case["name"])
            continue

        if kind == "unknown_operation":
            envelope = {
                "core_contract_version": "1.2",
                "operation": "unknown_authoring_operation",
                "request": {"operation": "unknown_authoring_operation"},
            }
            assert _errors(validator, envelope), case["name"]
            continue

        if kind == "missing_payload":
            envelope = {"core_contract_version": "1.2", "operation": "validate_authoring"}
            assert _errors(validator, envelope), case["name"]
            continue

        if kind == "both_payloads":
            envelope = _envelope(bound["C27"], "request", "validate_authoring")
            envelope["result"] = {"operation": "validate_authoring"}
            assert _errors(validator, envelope), case["name"]
            continue

        if kind == "unknown_transport_field":
            envelope = _envelope(bound["C27"], "request", "validate_authoring")
            envelope["transport_extension"] = True
            assert _errors(validator, envelope), case["name"]
            continue

        if kind in {"acc_invalid_request", "acc_invalid_result"}:
            envelope = _envelope(
                bound[case["source_case"]],
                "request" if kind == "acc_invalid_request" else "result",
                case["operation"],
            )
            _remove_path(
                envelope["request" if kind == "acc_invalid_request" else "result"],
                case["remove_path"],
            )
            assert not _errors(validator, envelope), case["name"]
            validate_semantic_core_protocol(envelope)
            definition = (
                "authoring_request" if kind == "acc_invalid_request" else "construction_result"
            )
            acc_schema = _document(ACC / "schema.json")
            assert _acc_errors(
                acc_schema,
                envelope["request" if kind == "acc_invalid_request" else "result"],
                definition,
            ), case["name"]
            continue

        raise AssertionError(f"unhandled protocol vector kind: {kind}")


def test_v12_wraps_all_bound_acc_cases_without_changing_semantics() -> None:
    protocol_validator = _protocol_validator()
    acc_schema = _document(ACC / "schema.json")
    bound = _bound_cases()

    assert list(bound) == [f"C{index:02d}" for index in range(1, 43)]
    for case in bound.values():
        operation = case["operation"]
        request_envelope = _envelope(case, "request")
        result_envelope = _envelope(case, "result")

        assert not _errors(protocol_validator, request_envelope), case["id"]
        assert not _errors(protocol_validator, result_envelope), case["id"]
        assert request_envelope["operation"] == request_envelope["request"]["operation"]
        assert result_envelope["operation"] == result_envelope["result"]["operation"]
        assert operation == request_envelope["operation"] == result_envelope["operation"]

        assert not _acc_errors(acc_schema, request_envelope["request"], "authoring_request"), case[
            "id"
        ]
        result_definition = (
            "validation_result" if operation == "validate_authoring" else "construction_result"
        )
        assert not _acc_errors(acc_schema, result_envelope["result"], result_definition), case["id"]


def test_v12_does_not_define_acc_semantic_fields_or_execute_authoring_operations() -> None:
    schema = _document(PROTOCOL / "contract.json")
    serialized = json.dumps(schema)
    for field in (
        "basis",
        "diagnostics",
        "outcome",
        "candidate_fragments",
        "normalized_result",
        "round_trip",
    ):
        assert f'"{field}"' not in serialized

    for path in (
        ROOT / "core" / "src" / "lib.rs",
        ROOT / "src" / "adr_kit" / "core" / "semantic_core.py",
        ROOT / "packages" / "node" / "src" / "node" / "core.ts",
    ):
        text = path.read_text(encoding="utf-8")
        assert "validate_authoring" not in text
        assert "construct_authoring_set" not in text
