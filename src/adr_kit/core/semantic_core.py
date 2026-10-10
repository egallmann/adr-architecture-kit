"""Direct Python binding for the versioned semantic-core contract.

The public SDK owns repository discovery and Python-native result mapping. The
semantic rules for the migrated operation execute in the packaged,
self-contained WASM artifact, so this module intentionally contains no
contract-validation rules. The Python host depends on ``wasmtime`` to load the
artifact; Rust build dependencies are compiled into the artifact itself.
"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from importlib import resources
from threading import Lock
from typing import Any

from jsonschema import Draft202012Validator
import wasmtime
import yaml

SEMANTIC_CORE_PROTOCOL_VERSIONS = ("1.0", "1.1", "1.2", "1.3", "1.4", "1.5")
SEMANTIC_CORE_PROTOCOL_V12_OPERATIONS = (
    "validate_authoring",
    "construct_authoring_set",
)
SEMANTIC_CORE_PROTOCOL_V13_OPERATIONS = ("materialize_architecture",)
SEMANTIC_CORE_PROTOCOL_V14_OPERATIONS = ("qualify_authoring_construction_1_1",)
SEMANTIC_CORE_PROTOCOL_V15_OPERATIONS = ("prepare_authoring_construction_basis_1_1",)


def semantic_core_capabilities() -> dict[str, object]:
    """Advertise the additive protocol capabilities reachable by this adapter."""

    return {
        "supported_versions": SEMANTIC_CORE_PROTOCOL_VERSIONS,
        "operations_by_version": {
            "1.2": SEMANTIC_CORE_PROTOCOL_V12_OPERATIONS,
            "1.3": SEMANTIC_CORE_PROTOCOL_V13_OPERATIONS,
            "1.4": SEMANTIC_CORE_PROTOCOL_V14_OPERATIONS,
            "1.5": SEMANTIC_CORE_PROTOCOL_V15_OPERATIONS,
        },
    }


def supports_semantic_core_operation(version: str, operation: str) -> bool:
    """Return whether an additive operation is reachable for an exact version."""

    return (
        (version == "1.2" and operation in SEMANTIC_CORE_PROTOCOL_V12_OPERATIONS)
        or (version == "1.3" and operation in SEMANTIC_CORE_PROTOCOL_V13_OPERATIONS)
        or (version == "1.4" and operation in SEMANTIC_CORE_PROTOCOL_V14_OPERATIONS)
        or (version == "1.5" and operation in SEMANTIC_CORE_PROTOCOL_V15_OPERATIONS)
    )


def _artifact_bytes() -> bytes:
    return resources.files("adr_kit.core").joinpath("semantic-core.wasm").read_bytes()


_runtime_lock = Lock()


@lru_cache(maxsize=1)
def _compile_semantic_core() -> tuple[wasmtime.Engine, wasmtime.Module]:
    """Compile the immutable core module once for this host process."""

    engine = wasmtime.Engine()
    return engine, wasmtime.Module(engine, _artifact_bytes())


def _compiled_semantic_core() -> tuple[wasmtime.Engine, wasmtime.Module]:
    # functools.lru_cache protects its data structure but may run the wrapped
    # function more than once when concurrent first callers miss together.
    # Serialize only initialization; request execution remains independent.
    with _runtime_lock:
        return _compile_semantic_core()


def execute_semantic_core_request(request: dict[str, Any]) -> dict[str, Any]:
    # The guest owns UUIDv7 construction; protocol 1.5 receives only the
    # environmental clock value needed by that algorithm. Never derive it
    # from candidate content or source ordering.
    request = dict(request)
    nested = request.get("request")
    if (
        request.get("core_contract_version") == "1.5"
        and request.get("operation") == "prepare_authoring_construction_basis_1_1"
        and isinstance(nested, dict)
        and "identity_clock_ms" not in nested
    ):
        request["request"] = dict(nested)
        request["request"]["identity_clock_ms"] = time.time_ns() // 1_000_000
    payload = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    engine, module = _compiled_semantic_core()
    store = wasmtime.Store(engine)
    instance = wasmtime.Instance(store, module, [])
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


@lru_cache(maxsize=len(SEMANTIC_CORE_PROTOCOL_VERSIONS))
def _protocol_validator(version: str = "1.0") -> Draft202012Validator:
    """Load the validator selected by the declared semantic-core version.

    v1.0 remains the compatibility fallback for unknown declarations because
    the Rust boundary emits its established v1.0 invalid-request envelope for
    those requests. v1.1 and v1.2 are intentionally separate canonical
    schemas rather than mutations of the packaged v1.0 contract.
    """
    filename = {
        "1.0": "semantic-core-contract.json",
        "1.1": "semantic-core-contract-v1.1.json",
        "1.2": "semantic-core-contract-v1.2.json",
        "1.3": "semantic-core-contract-v1.3.json",
        "1.4": "semantic-core-contract-v1.4.json",
        "1.5": "semantic-core-contract-v1.5.json",
    }.get(version, "semantic-core-contract.json")
    contract = json.loads(
        resources.files("adr_kit.core").joinpath(filename).read_text(encoding="utf-8")
    )
    return Draft202012Validator(contract)


def validate_semantic_core_protocol(value: dict[str, Any]) -> None:
    """Assert that a host request/result obeys the versioned transport schema."""

    declared_version = value.get("core_contract_version")
    version = (
        declared_version
        if declared_version in {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5"}
        else "1.0"
    )
    errors = sorted(
        _protocol_validator(version).iter_errors(value), key=lambda error: list(error.path)
    )
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
