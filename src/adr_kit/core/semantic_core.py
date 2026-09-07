"""Direct Python binding for the versioned semantic-core contract.

The public SDK owns repository discovery and Python-native result mapping. The
semantic rules for the migrated operation execute in the packaged,
self-contained WASM artifact, so this module intentionally contains no
contract-validation rules. The Python host depends on ``wasmtime`` to load the
artifact; Rust build dependencies are compiled into the artifact itself.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator
import wasmtime
import yaml


def _artifact_bytes() -> bytes:
    return resources.files("adr_kit.core").joinpath("semantic-core.wasm").read_bytes()


def execute_semantic_core_request(request: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    store = wasmtime.Store()
    instance = wasmtime.Instance(store, wasmtime.Module(store.engine, _artifact_bytes()), [])
    exports: Any = instance.exports(store)
    memory = exports["memory"]
    alloc = exports["alloc"]
    execute = exports["execute"]
    result_len = exports["result_len"]
    dealloc = exports["dealloc"]
    input_pointer = alloc(store, len(payload))
    memory.write(store, payload, input_pointer)
    output_pointer = execute(store, input_pointer, len(payload))
    output_size = result_len(store)
    try:
        result = bytes(memory.read(store, output_pointer, output_pointer + output_size))
    finally:
        dealloc(store, output_pointer, output_size)
        dealloc(store, input_pointer, len(payload))
    decoded = json.loads(result)
    if not isinstance(decoded, dict):
        raise RuntimeError("semantic core returned a non-object result")
    return decoded


@lru_cache(maxsize=1)
def _protocol_validator() -> Draft202012Validator:
    contract = json.loads(
        resources.files("adr_kit.core")
        .joinpath("semantic-core-contract.json")
        .read_text(encoding="utf-8")
    )
    return Draft202012Validator(contract)


def validate_semantic_core_protocol(value: dict[str, Any]) -> None:
    """Assert that a host request/result obeys the versioned transport schema."""

    errors = sorted(_protocol_validator().iter_errors(value), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors[:3]
        )
        raise ValueError(f"semantic-core protocol violation: {details}")


def _execute_validated(request: dict[str, Any]) -> dict[str, Any]:
    validate_semantic_core_protocol(request)
    result = execute_semantic_core_request(request)
    validate_semantic_core_protocol(result)
    return result


def execute_validated_semantic_core_request(request: dict[str, Any]) -> dict[str, Any]:
    """Execute one protocol-valid request and validate its core result envelope."""

    return _execute_validated(request)


def execute_contract_validation(
    *,
    profile: str,
    entity_registry: Any,
    remediation_ledger: Any | None,
    max_sentinel_fields: int | None,
    max_non_complete_entities: int | None,
) -> dict[str, Any]:
    """Execute normalized contract validation through the shared core."""

    def dump(value: Any) -> Any:
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return model_dump(mode="json")
        return value

    request: dict[str, Any] = {
        "core_contract_version": "1.0",
        "operation": "validate_contract",
        "profile": profile,
        "entity_registry": dump(entity_registry),
        "remediation_ledger": dump(remediation_ledger),
    }
    if max_sentinel_fields is not None:
        request["max_sentinel_fields"] = max_sentinel_fields
    if max_non_complete_entities is not None:
        request["max_non_complete_entities"] = max_non_complete_entities
    return _execute_validated(request)


def execute_project_metadata_validation(project_root: Any) -> dict[str, Any]:
    """Validate PROJECT.yaml through the shared semantic core."""

    path = project_root / "PROJECT.yaml"
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        result = {
            "core_contract_version": "1.0",
            "operation": "validate_project_metadata",
            "success": False,
            "diagnostics": [
                {
                    "severity": "error",
                    "code": "project_metadata.parse_error",
                    "message": str(exc),
                    "path": "PROJECT.yaml",
                }
            ],
        }
        validate_semantic_core_protocol(result)
        return result
    if not isinstance(payload, dict):
        payload = None
    return _execute_validated(
        {
            "core_contract_version": "1.0",
            "operation": "validate_project_metadata",
            "project_metadata": payload,
        }
    )


def execute_provider_registry(bindings: list[dict[str, str]]) -> dict[str, Any]:
    """Validate deterministic provider routing through the shared core."""

    return _execute_validated(
        {
            "core_contract_version": "1.0",
            "operation": "open_provider_registry",
            "bindings": bindings,
        }
    )


def execute_repository_validation(
    *,
    model_version: str,
    architecture_namespace: str | None,
    entities: Any,
) -> dict[str, Any]:
    """Validate normalized repository identity through the shared core."""

    def dump(value: Any) -> Any:
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return model_dump(mode="json")
        return value

    return _execute_validated(
        {
            "core_contract_version": "1.0",
            "operation": "open_repository",
            "model_version": model_version,
            "architecture_namespace": architecture_namespace,
            "entities": [dump(entity) for entity in entities],
        }
    )


def execute_generated_artifact_classification(
    *,
    artifact_kind: str,
    declared_artifact_kind: str | None,
    header_valid: bool,
    header_error: str | None,
    declared_source_hash: str | None,
    declared_rendered_hash: str | None,
    actual_rendered_hash: str | None,
    expected_source_hash: str | None,
    expected_rendered_hash: str | None,
) -> dict[str, Any]:
    """Classify normalized generated-artifact integrity facts through the core."""

    return _execute_validated(
        {
            "core_contract_version": "1.0",
            "operation": "classify_generated_artifact",
            "artifact_kind": artifact_kind,
            "declared_artifact_kind": declared_artifact_kind,
            "header_valid": header_valid,
            "header_error": header_error,
            "declared_source_hash": declared_source_hash,
            "declared_rendered_hash": declared_rendered_hash,
            "actual_rendered_hash": actual_rendered_hash,
            "expected_source_hash": expected_source_hash,
            "expected_rendered_hash": expected_rendered_hash,
        }
    )


def execute_architecture_reference_validation(
    *,
    records: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate normalized ADR cross-reference facts through the shared core."""

    return _execute_validated(
        {
            "core_contract_version": "1.0",
            "operation": "validate_architecture_references",
            "records": records,
            "reviews": reviews,
            "overrides": overrides,
        }
    )


def execute_architecture_validation(
    *,
    records: list[dict[str, Any]],
    mode: str,
) -> dict[str, Any]:
    """Evaluate normalized ADR business rules through the shared core."""

    return _execute_validated(
        {
            "core_contract_version": "1.0",
            "operation": "validate_architecture",
            "mode": mode,
            "records": records,
        }
    )


def execute_attribution_shim_generation(
    *, language: str, vocabulary: dict[str, Any]
) -> dict[str, Any]:
    """Render one canonical attribution shim through the shared core."""

    return _execute_validated(
        {
            "core_contract_version": "1.0",
            "operation": "generate_attribution_shim",
            "language": language,
            "vocabulary": vocabulary,
        }
    )
