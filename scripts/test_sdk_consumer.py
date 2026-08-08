"""Exercise the supported SDK as a real external consumer."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
import tempfile
from collections.abc import Iterable
from contextlib import nullcontext
from dataclasses import fields, is_dataclass
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

PINNED_TIMESTAMP = "2026-01-01T00:00:00Z"
DIST_NAME = "adr-architecture-kit"


def _compiler_types(value: object) -> set[str]:
    pending = [value]
    visited: set[int] = set()
    leaked: set[str] = set()
    while pending:
        current = pending.pop()
        identity = id(current)
        if identity in visited:
            continue
        visited.add(identity)
        module = type(current).__module__
        if module.startswith("adr_kit.compiler"):
            leaked.add(f"{module}.{type(current).__name__}")
        if is_dataclass(current):
            pending.extend(getattr(current, field.name) for field in fields(current))
        elif isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())
        elif isinstance(current, (list, tuple, set, frozenset)):
            pending.extend(current)
    return leaked


def run_consumer(project_root: Path, version_source: str) -> dict[str, object]:
    """Run the SDK workflow and return a JSON-safe evidence summary."""

    version_context = (
        patch(
            "importlib.metadata.version",
            side_effect=importlib.metadata.PackageNotFoundError,
        )
        if version_source == "source"
        else nullcontext()
    )
    with version_context:
        from adr_kit.api import (
            CompilationRequest,
            ValidationRequest,
            capabilities,
            compile_architecture,
            open_repository,
            validate_architecture,
        )

    project_root = project_root.resolve()
    manifest = capabilities()
    if version_source == "metadata":
        expected_version = importlib.metadata.version(DIST_NAME)
        if manifest.package_version != expected_version:
            raise AssertionError("SDK package version does not match installed metadata")
    elif manifest.package_version == "0+unknown":
        raise AssertionError("direct-source version fallback did not resolve pyproject.toml")

    validation = validate_architecture(ValidationRequest(project_root, cross_references=True))
    if not validation.success:
        raise AssertionError(f"SDK validation failed: {validation.diagnostics}")

    preview = compile_architecture(CompilationRequest(project_root, timestamp=PINNED_TIMESTAMP))
    if not preview.success or preview.model is None or preview.fingerprint is None:
        raise AssertionError(f"SDK preview failed: {preview.diagnostics}")
    if any(artifact.written_path is not None for artifact in preview.artifacts):
        raise AssertionError("preview unexpectedly reported written paths")
    for artifact in preview.artifacts:
        if artifact.size_bytes != len(artifact.content):
            raise AssertionError(f"artifact size mismatch: {artifact.artifact_id}")
        if artifact.sha256 != sha256(artifact.content).hexdigest():
            raise AssertionError(f"artifact hash mismatch: {artifact.artifact_id}")

    with tempfile.TemporaryDirectory(prefix="adr-kit-sdk-consumer-") as temporary:
        output_root = Path(temporary) / "written"
        output_root.mkdir()
        shutil.copy2(project_root / "PROJECT.yaml", output_root / "PROJECT.yaml")
        written = compile_architecture(
            CompilationRequest(
                project_root,
                write=True,
                output_root=output_root,
                timestamp=PINNED_TIMESTAMP,
            )
        )
        if not written.success:
            raise AssertionError(f"SDK write failed: {written.diagnostics}")
        if {item.relative_path: item.content for item in preview.artifacts} != {
            item.relative_path: item.content for item in written.artifacts
        }:
            raise AssertionError("preview and write bytes differ")
        repository = open_repository(output_root)
        if repository.fingerprint() != preview.fingerprint:
            raise AssertionError("preview and repository fingerprints differ")

    leaks: set[str] = set()
    for value in (manifest, validation, preview, written):
        leaks.update(_compiler_types(value))
    if leaks:
        raise AssertionError(f"compiler types crossed SDK facade: {sorted(leaks)}")

    versions = {
        manifest.package_version,
        validation.package_version,
        preview.package_version,
        written.package_version,
    }
    if len(versions) != 1:
        raise AssertionError(f"SDK version drift: {sorted(versions)}")
    if manifest.api_contract_version != "1.0":
        raise AssertionError("unexpected SDK contract version")

    return {
        "api_contract_version": manifest.api_contract_version,
        "package_version": manifest.package_version,
        "validated_files": len(validation.validated_files),
        "artifact_ids": sorted(item.artifact_id for item in preview.artifacts),
        "fingerprint": preview.fingerprint,
        "compiler_types": sorted(leaks),
        "version_source": version_source,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--version-source", choices=("source", "metadata"), required=True)
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    evidence = run_consumer(arguments.project_root, arguments.version_source)
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
