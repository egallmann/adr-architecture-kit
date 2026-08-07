"""Operation-level truth tables for the narrow Phase 1 SDK."""

from __future__ import annotations

from hashlib import sha256
from importlib import import_module
from pathlib import Path
from shutil import copy2
from types import ModuleType
from typing import Any

import pytest

from adr_kit.repository import ArchitectureRepository
from tests.test_architecture_index_generator import _create_fixture

PINNED_TIMESTAMP = "2026-01-01T00:00:00Z"


def _api() -> ModuleType:
    return import_module("adr_kit.api")


def _fixture(root: Path) -> Path:
    _create_fixture(root)
    return root


def _preview(api: ModuleType, root: Path) -> Any:
    return api.compile_architecture(api.CompilationRequest(root, timestamp=PINNED_TIMESTAMP))


def test_validate_architecture_success_warning_and_failure(tmp_path: Path) -> None:
    api = _api()
    root = _fixture(tmp_path / "project")

    success = api.validate_architecture(api.ValidationRequest(root, cross_references=True))
    assert success.success is True
    assert success.error_count == 0
    assert success.validated_files == tuple(sorted(success.validated_files))
    assert all("\\" not in path for path in success.validated_files)

    logical_path = root / "adrs" / "logical" / "ADR-L-1000-discovery.yaml"
    original = logical_path.read_text(encoding="utf-8")
    logical_path.write_text(
        original.replace("Discovery fixture.", "The package boundary is discussed."),
        encoding="utf-8",
    )
    warning = api.validate_architecture(api.ValidationRequest(root))
    assert warning.success is True
    assert warning.warning_count >= 1
    assert any(
        item.severity == "warning" and item.code == "INV-0002" for item in warning.diagnostics
    )

    logical_path.write_text(
        "\n".join(line for line in original.splitlines() if not line.startswith("title:")) + "\n",
        encoding="utf-8",
    )
    failure = api.validate_architecture(api.ValidationRequest(root))
    assert failure.success is False
    assert failure.error_count >= 1
    assert any(item.severity == "error" for item in failure.diagnostics)


def test_compile_preview_truth_table(tmp_path: Path) -> None:
    api = _api()
    root = _fixture(tmp_path / "project")

    result = _preview(api, root)

    assert result.success is True
    assert result.partial is False
    assert result.artifacts
    assert result.artifacts_emitted == len(result.artifacts)
    assert result.model is not None
    assert result.fingerprint == result.model.fingerprint
    assert all(artifact.written_path is None for artifact in result.artifacts)
    assert all(not (root / artifact.relative_path).exists() for artifact in result.artifacts)
    assert [artifact.relative_path for artifact in result.artifacts] == sorted(
        artifact.relative_path for artifact in result.artifacts
    )


def test_compile_write_truth_table(tmp_path: Path) -> None:
    api = _api()
    root = _fixture(tmp_path / "project")
    output_root = tmp_path / "written"
    output_root.mkdir()
    copy2(root / "PROJECT.yaml", output_root / "PROJECT.yaml")

    preview = _preview(api, root)
    written = api.compile_architecture(
        api.CompilationRequest(
            root,
            write=True,
            output_root=output_root,
            timestamp=PINNED_TIMESTAMP,
        )
    )

    assert written.success is True
    assert written.partial is False
    assert {item.relative_path: item.content for item in written.artifacts} == {
        item.relative_path: item.content for item in preview.artifacts
    }
    for artifact in written.artifacts:
        expected_path = (output_root / artifact.relative_path).resolve()
        assert artifact.written_path == expected_path
        assert expected_path.read_bytes() == artifact.content


def test_compile_failure_truth_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = _api()
    root = _fixture(tmp_path / "project")
    logical_path = root / "adrs" / "logical" / "ADR-L-1000-discovery.yaml"
    original = logical_path.read_text(encoding="utf-8")
    logical_path.write_text(
        original.replace(
            "context: |\n  Discovery fixture.\n",
            "context: |\n  Discovery fixture.\n"
            "governance:\n"
            "  steelman_review_required: true\n"
            "  steelman_review_completed: false\n"
            "  implementation_authority: implementation_authoritative\n"
            "  approved_by: erik\n"
            '  approved_date: "2026-03-18T12:00:00Z"\n',
        ),
        encoding="utf-8",
    )

    diagnostic_failure = _preview(api, root)
    assert diagnostic_failure.success is False
    assert any(item.severity == "error" for item in diagnostic_failure.diagnostics)
    assert diagnostic_failure.partial is bool(diagnostic_failure.artifacts)
    if not diagnostic_failure.artifacts:
        assert diagnostic_failure.model is None
        assert diagnostic_failure.fingerprint is None

    logical_path.write_text("not: [valid", encoding="utf-8")
    with pytest.raises(api.OperationError) as parser_failure:
        _preview(api, root)
    assert parser_failure.value.__cause__ is not None

    operations = import_module("adr_kit.api._operations")

    def explode(*_args: object, **_kwargs: object) -> None:
        raise OSError("compiler I/O failure")

    monkeypatch.setattr(operations.ArchitectureCompiler, "compile", explode)
    with pytest.raises(api.OperationError) as raised:
        _preview(api, _fixture(tmp_path / "unexpected"))
    assert isinstance(raised.value.__cause__, OSError)


def test_artifact_descriptor_ids_paths_hashes_and_integrity(tmp_path: Path) -> None:
    api = _api()
    result = _preview(api, _fixture(tmp_path / "project"))

    by_id = {artifact.artifact_id: artifact for artifact in result.artifacts}
    required_ids = {
        "manifest",
        "architecture-index",
        "entity-registry",
        "relationship-registry",
        "unresolved-registry",
        "decision-registry",
        "capability-registry",
        "invariant-registry",
        "component-registry",
        "system-registry",
        "legacy-entity-registry",
        "rendered-adr:ADR-L-1000",
        "rendered-adr:ADR-PC-1000",
        "rendered-adr:ADR-PS-1000",
    }
    assert required_ids <= set(by_id)

    for artifact in result.artifacts:
        assert artifact.group in {"registries", "manifest", "markdown"}
        assert "\\" not in artifact.relative_path
        assert not artifact.relative_path.startswith("/")
        assert artifact.size_bytes == len(artifact.content)
        assert artifact.sha256 == sha256(artifact.content).hexdigest()
        assert len(artifact.sha256) == 64
        if artifact.integrity_header is not None:
            assert artifact.content.startswith(artifact.integrity_header.encode("utf-8"))


def test_open_repository_returns_loaded_stable_repository(tmp_path: Path) -> None:
    api = _api()
    root = _fixture(tmp_path / "project")
    api.compile_architecture(api.CompilationRequest(root, write=True, timestamp=PINNED_TIMESTAMP))

    repository = api.open_repository(root)

    assert isinstance(repository, ArchitectureRepository)
    assert repository.mode == "normalized"
    assert repository.get_model().fingerprint == repository.fingerprint()


def test_compile_model_matches_repository_fingerprint(tmp_path: Path) -> None:
    api = _api()
    root = _fixture(tmp_path / "project")

    preview = _preview(api, root)
    written = api.compile_architecture(
        api.CompilationRequest(root, write=True, timestamp=PINNED_TIMESTAMP)
    )
    repository = api.open_repository(root)

    assert preview.fingerprint == written.fingerprint
    assert preview.fingerprint == repository.fingerprint()
    assert preview.model is not None
    assert preview.model.model_dump(mode="json") == repository.get_model().model_dump(mode="json")


def test_returned_model_is_detached(tmp_path: Path) -> None:
    api = _api()
    root = _fixture(tmp_path / "project")

    first = _preview(api, root)
    assert first.model is not None
    original_ids = first.model.entity_ids()
    first.model.entities.clear()

    second = _preview(api, root)
    assert second.model is not None
    assert second.model.entity_ids() == original_ids
    assert second.fingerprint == first.fingerprint
