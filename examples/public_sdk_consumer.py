"""Minimal consumer of the supported adr_kit.api boundary."""

from __future__ import annotations

import argparse
from pathlib import Path

from adr_kit.api import (
    CompilationRequest,
    ValidationRequest,
    capabilities,
    compile_architecture,
    validate_architecture,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    arguments = parser.parse_args()

    manifest = capabilities()
    validation = validate_architecture(
        ValidationRequest(arguments.project_root, cross_references=True)
    )
    if not validation.success:
        for diagnostic in validation.diagnostics:
            print(diagnostic.severity, diagnostic.code, diagnostic.message)
        return 1

    compilation = compile_architecture(
        CompilationRequest(
            arguments.project_root,
            timestamp="2026-01-01T00:00:00Z",
        )
    )
    print(f"package={manifest.package_version} api={manifest.api_contract_version}")
    print(f"fingerprint={compilation.fingerprint}")
    for artifact in compilation.artifacts:
        print(artifact.artifact_id, artifact.relative_path, artifact.sha256)
    return 0 if compilation.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
