"""Executable contract for the narrow supported Phase 1 SDK boundary."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, get_args, get_origin, get_type_hints

import pytest

import adr_kit
from adr_kit.repository import ArchitectureRegistryError
from tests.test_architecture_index_generator import _create_fixture

EXPECTED_PUBLIC_SYMBOLS = [
    "ArchitectureRepository",
    "NormalizedArchitectureModel",
    "ArtifactDescriptor",
    "CapabilityManifest",
    "ValidationRequest",
    "ValidationResult",
    "CompilationRequest",
    "CompilationResult",
    "PromotionPrepareRequest",
    "PromotionPrepareResult",
    "PromotionCheckRequest",
    "PromotionCheckResult",
    "PromotionApplyRequest",
    "PromotionApplyResult",
    "PromotionMutationDescriptor",
    "PromotionBindingDescriptor",
    "PromotionValidationEvidenceDescriptor",
    "PromotionBlockerDescriptor",
    "PromotionBaselineDescriptor",
    "PromotionExecutionEvidenceDescriptor",
    "Diagnostic",
    "SDKError",
    "InvalidRequestError",
    "OperationError",
    "RepositoryError",
    "capabilities",
    "validate_architecture",
    "compile_architecture",
    "open_repository",
    "prepare_promotion",
    "check_promotion",
    "apply_promotion",
]


def _api() -> ModuleType:
    return import_module("adr_kit.api")


def _annotation_modules(annotation: object) -> set[str]:
    modules: set[str] = set()
    module = getattr(annotation, "__module__", None)
    if isinstance(module, str):
        modules.add(module)
    origin = get_origin(annotation)
    if origin is not None:
        modules.update(_annotation_modules(origin))
    for argument in get_args(annotation):
        modules.update(_annotation_modules(argument))
    return modules


def _public_annotations(api: ModuleType) -> list[object]:
    annotations: list[object] = []
    for name in api.__all__:
        value = getattr(api, name)
        if isinstance(value, type) and is_dataclass(value):
            annotations.extend(field.type for field in fields(value))
        if callable(value):
            annotations.extend(get_type_hints(value).values())
    return annotations


def test_api_symbol_inventory_matches_contract() -> None:
    api = _api()

    assert api.__all__ == EXPECTED_PUBLIC_SYMBOLS
    assert sorted(name for name in vars(api) if not name.startswith("_")) == sorted(
        EXPECTED_PUBLIC_SYMBOLS
    )


def test_api_imports_from_supported_module() -> None:
    api = _api()

    for symbol in EXPECTED_PUBLIC_SYMBOLS:
        assert getattr(api, symbol) is not None
        assert not hasattr(adr_kit, symbol), f"{symbol} must not be re-exported from adr_kit root"

    assert api.ArchitectureRepository.__module__.startswith("adr_kit.repository")
    assert api.NormalizedArchitectureModel.__module__.startswith("adr_kit.models")


def test_public_annotations_exclude_compiler_modules() -> None:
    api = _api()

    leaking_modules = {
        module
        for annotation in _public_annotations(api)
        for module in _annotation_modules(annotation)
        if module.startswith("adr_kit.compiler")
    }

    assert leaking_modules == set()


def test_requests_reject_invalid_roots_modes_groups_and_timestamps(tmp_path: Path) -> None:
    api = _api()
    missing = tmp_path / "missing"

    with pytest.raises(api.InvalidRequestError):
        api.ValidationRequest(missing)

    root = tmp_path / "project"
    _create_fixture(root)

    with pytest.raises(api.InvalidRequestError):
        api.ValidationRequest(root, mode="wide")
    with pytest.raises(api.InvalidRequestError):
        api.CompilationRequest(root, artifact_groups=())
    with pytest.raises(api.InvalidRequestError):
        api.CompilationRequest(root, artifact_groups=("manifest", "manifest"))
    with pytest.raises(api.InvalidRequestError):
        api.CompilationRequest(root, artifact_groups=("graph",))
    with pytest.raises(api.InvalidRequestError):
        api.CompilationRequest(root, output_root=tmp_path / "out")
    with pytest.raises(api.InvalidRequestError):
        api.CompilationRequest(root, timestamp="2026-01-01")
    with pytest.raises(api.InvalidRequestError):
        api.CompilationRequest(root, timestamp="2026-01-01T00:00:00+01:00")

    validation = api.ValidationRequest(root)
    compilation = api.CompilationRequest(
        root,
        artifact_groups=("markdown", "registries", "manifest"),
        timestamp="2026-01-01T00:00:00Z",
    )

    assert validation.project_root == root.resolve()
    assert compilation.project_root == root.resolve()
    assert compilation.artifact_groups == ("registries", "manifest", "markdown")


def test_public_contracts_are_frozen(tmp_path: Path) -> None:
    api = _api()
    root = tmp_path / "project"
    _create_fixture(root)

    contract_names = (
        "ArtifactDescriptor",
        "CapabilityManifest",
        "ValidationRequest",
        "ValidationResult",
        "CompilationRequest",
        "CompilationResult",
        "PromotionPrepareRequest",
        "PromotionPrepareResult",
        "PromotionCheckRequest",
        "PromotionCheckResult",
        "PromotionApplyRequest",
        "PromotionApplyResult",
        "PromotionMutationDescriptor",
        "PromotionBindingDescriptor",
        "PromotionValidationEvidenceDescriptor",
        "PromotionBlockerDescriptor",
        "PromotionBaselineDescriptor",
        "PromotionExecutionEvidenceDescriptor",
        "Diagnostic",
    )
    for name in contract_names:
        contract = getattr(api, name)
        assert is_dataclass(contract)
        assert getattr(contract, "__dataclass_params__").frozen is True
        assert "__dict__" not in getattr(contract, "__slots__")

    request = api.ValidationRequest(root)
    with pytest.raises(FrozenInstanceError):
        request.mode = "structural"


def test_sdk_error_hierarchy_and_chaining(tmp_path: Path) -> None:
    api = _api()

    assert issubclass(api.InvalidRequestError, api.SDKError)
    assert issubclass(api.InvalidRequestError, ValueError)
    assert issubclass(api.OperationError, api.SDKError)
    assert issubclass(api.RepositoryError, api.OperationError)

    root = tmp_path / "project"
    _create_fixture(root)
    with pytest.raises(api.RepositoryError) as raised:
        api.open_repository(root)

    assert isinstance(raised.value.__cause__, ArchitectureRegistryError)


def test_capability_manifest_is_exact_and_deterministic() -> None:
    api = _api()

    first = api.capabilities()
    second = api.capabilities()

    assert first == second
    assert first.api_contract_version == "1.0"
    assert first.operations == (
        "capabilities",
        "validate_architecture",
        "compile_architecture",
        "open_repository",
        "prepare_promotion",
        "check_promotion",
        "apply_promotion",
    )
    assert hasattr(first, "supported_promotion_contract_versions")
    assert first.supported_promotion_contract_versions == (
        "ste.design_journal.promotion_contract/v0.1",
    )
    assert first.validation_modes == ("complete", "structural")
    assert first.artifact_groups == ("registries", "manifest", "markdown")
    assert first.supported_adr_schema_versions == ("1.0", "1.1", "1.2")
    assert first.stable_adr_schema_versions == ("1.0",)
    assert first.provisional_adr_schema_versions == ("1.1", "1.2")
    assert "1.3" not in first.supported_adr_schema_versions
    assert first.normalized_model_schema_version == "1.1"
    assert list(first.as_dict()) == [field.name for field in fields(first)]
    assert all(not isinstance(value, tuple) for value in first.as_dict().values())


def test_result_object_graph_excludes_compiler_types(tmp_path: Path) -> None:
    api = _api()
    root = tmp_path / "project"
    _create_fixture(root)

    result = api.compile_architecture(
        api.CompilationRequest(root, timestamp="2026-01-01T00:00:00Z")
    )
    pending: list[Any] = [result]
    visited: set[int] = set()
    leaked: set[str] = set()

    while pending:
        value = pending.pop()
        identity = id(value)
        if identity in visited:
            continue
        visited.add(identity)
        module = type(value).__module__
        if module.startswith("adr_kit.compiler"):
            leaked.add(f"{module}.{type(value).__name__}")
        if is_dataclass(value):
            pending.extend(getattr(value, field.name) for field in fields(value))
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            pending.extend(value)

    assert leaked == set()
