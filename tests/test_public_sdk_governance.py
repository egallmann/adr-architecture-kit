"""Focused tests for the public governance and compiler SDK slice."""

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path

import pytest
import yaml

from adr_kit.api import (
    CompilationRequest,
    ContractValidationRequest,
    GeneratedDocsValidationRequest,
    ProjectMetadataValidationRequest,
    compile_architecture,
    validate_contract,
    validate_generated_docs,
    validate_project_metadata,
)
from adr_kit.api import _operations as operations
from adr_kit.integrity import GeneratedArtifactStatus
from tests.test_architecture_index_generator import _create_fixture
from tests.test_architecture_repository import _generate_bundle

PINNED_TIMESTAMP = "2026-01-01T00:00:00Z"


def test_project_metadata_sdk_returns_completed_expected_results(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)

    valid = validate_project_metadata(ProjectMetadataValidationRequest(root))
    assert valid.success is True
    assert valid.diagnostics == ()

    (root / "PROJECT.yaml").write_text("project: [malformed", encoding="utf-8")
    invalid = validate_project_metadata(ProjectMetadataValidationRequest(root))
    assert invalid.success is False
    assert invalid.diagnostics[0].path == "PROJECT.yaml"
    assert invalid.diagnostics[0].severity == "error"


def test_project_metadata_sdk_wraps_unexpected_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    _create_fixture(root)

    def exploding_core(_project_root: Path) -> dict[str, object]:
        raise OSError("metadata I/O failure")

    monkeypatch.setattr(operations, "execute_project_metadata_validation", exploding_core)
    with pytest.raises(operations.OperationError) as raised:
        validate_project_metadata(ProjectMetadataValidationRequest(root))
    assert isinstance(raised.value.__cause__, OSError)


def test_contract_sdk_preserves_profile_issues_and_threshold_semantics(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _generate_bundle(root)

    valid = validate_contract(ContractValidationRequest(root))
    assert valid.success is True
    assert valid.outcome == "compliant"
    assert valid.issues == ()

    entity_path = root / "adrs" / "index" / "entity-registry.yaml"
    entity_data = yaml.safe_load(entity_path.read_text(encoding="utf-8"))
    component = next(
        entity for entity in entity_data["entities"] if entity["entity_type"] == "component"
    )
    component["metadata"]["module_path"] = "__NOT_YET_MODELED__"
    entity_path.write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    brownfield = validate_contract(ContractValidationRequest(root, profile="brownfield"))
    assert brownfield.success is True
    assert brownfield.outcome == "sentinel_compliant"
    assert brownfield.sentinel_field_count == 1
    assert (
        validate_contract(
            ContractValidationRequest(root, profile="brownfield", max_sentinel_fields=1)
        ).success
        is True
    )
    exceeded = validate_contract(
        ContractValidationRequest(root, profile="brownfield", max_sentinel_fields=0)
    )
    assert exceeded.success is False
    assert exceeded.outcome == "sentinel_compliant"
    assert any(item.code == "contract.max_sentinel_fields" for item in exceeded.diagnostics)


def test_contract_sdk_preserves_invalid_issues_and_non_complete_threshold(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    _generate_bundle(root)
    entity_path = root / "adrs" / "index" / "entity-registry.yaml"
    entity_data = yaml.safe_load(entity_path.read_text(encoding="utf-8"))
    capability = next(
        entity for entity in entity_data["entities"] if entity["entity_type"] == "capability"
    )
    del capability["metadata"]["adr_id"]
    capability["completeness"]["status"] = "partial"
    capability["completeness"]["missing_fields"] = ["summary"]
    entity_path.write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")

    invalid = validate_contract(ContractValidationRequest(root, profile="greenfield"))
    assert invalid.success is False
    assert invalid.outcome == "non_compliant"
    assert invalid.issues
    assert all(issue.path and issue.message for issue in invalid.issues)

    capability["metadata"]["adr_id"] = "ADR-L-1000"
    entity_path.write_text(yaml.safe_dump(entity_data, sort_keys=False), encoding="utf-8")
    brownfield = validate_contract(ContractValidationRequest(root, profile="brownfield"))
    assert brownfield.success is True
    assert brownfield.non_complete_entity_count == 1
    exceeded = validate_contract(
        ContractValidationRequest(root, profile="brownfield", max_non_complete_entities=0)
    )
    assert exceeded.success is False
    assert any(item.code == "contract.max_non_complete_entities" for item in exceeded.diagnostics)


def test_contract_request_rejects_invalid_profile_and_thresholds(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    with pytest.raises(ValueError):
        ContractValidationRequest(root, profile="unsupported")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ContractValidationRequest(root, max_sentinel_fields=-1)
    with pytest.raises(ValueError):
        ContractValidationRequest(root, max_non_complete_entities=True)  # type: ignore[arg-type]


def test_generated_docs_sdk_translates_integrity_results_and_containment(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    written = compile_architecture(CompilationRequest(root, write=True, timestamp=PINNED_TIMESTAMP))
    assert written.success is True

    valid = validate_generated_docs(GeneratedDocsValidationRequest(root))
    assert valid.success is True
    assert valid.artifacts
    assert [item.artifact_path for item in valid.artifacts] == sorted(
        item.artifact_path for item in valid.artifacts
    )
    assert all(type(item).__module__ != "adr_kit.integrity.validation" for item in valid.artifacts)
    assert all(is_dataclass(item) and "__dict__" not in item.__slots__ for item in valid.artifacts)

    target = root / valid.artifacts[0].artifact_path
    target.write_text(target.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
    tampered = validate_generated_docs(GeneratedDocsValidationRequest(root))
    assert tampered.success is False
    assert any(
        item.status == GeneratedArtifactStatus.TAMPERED_GENERATED_OUTPUT.value
        for item in tampered.artifacts
    )


def test_compile_sdk_check_and_system_overview_selection(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _create_fixture(root)
    default = compile_architecture(CompilationRequest(root, timestamp=PINNED_TIMESTAMP))
    assert any(item.relative_path == "SYSTEM-OVERVIEW.md" for item in default.artifacts)

    selected = compile_architecture(
        CompilationRequest(
            root,
            artifact_groups=("registries", "manifest", "markdown"),
            include_system_overview=False,
            timestamp=PINNED_TIMESTAMP,
        )
    )
    paths = {item.relative_path for item in selected.artifacts}
    assert "SYSTEM-OVERVIEW.md" not in paths
    assert "adrs/manifest.yaml" in paths
    assert "adrs/entities/registry.yaml" in paths
    assert any(path.startswith("adrs/adr-projection/") for path in paths)

    compile_architecture(CompilationRequest(root, write=True, timestamp=PINNED_TIMESTAMP))
    checked = compile_architecture(CompilationRequest(root, check=True, timestamp=PINNED_TIMESTAMP))
    assert checked.success is True
    (root / "adrs" / "manifest.yaml").write_bytes(b"drift\n")
    drift = compile_architecture(CompilationRequest(root, check=True, timestamp=PINNED_TIMESTAMP))
    assert drift.success is False
    assert any(item.code == "E702" for item in drift.diagnostics)

    with pytest.raises(ValueError):
        CompilationRequest(root, check=True, write=True)
