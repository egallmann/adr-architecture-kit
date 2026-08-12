"""Post-apply regeneration and validation coordination."""

from __future__ import annotations

from pathlib import Path

from ..api._contracts import CompilationRequest, Diagnostic, ValidationRequest
from ..api._operations import compile_architecture, validate_architecture


def regenerate_and_validate(
    project_root: Path,
    *,
    timestamp: str | None = None,
) -> tuple[bool, bool, str | None, tuple[Diagnostic, ...]]:
    """Compile derived artifacts then validate corpus.

    Returns (regeneration_completed, validation_success, fingerprint, diagnostics)
    """

    compile_result = compile_architecture(
        CompilationRequest(
            project_root=project_root,
            artifact_groups=("registries", "manifest", "markdown"),
            write=True,
            timestamp=timestamp,
        )
    )
    if not compile_result.success:
        return False, False, None, tuple(compile_result.diagnostics)

    second = compile_architecture(
        CompilationRequest(
            project_root=project_root,
            artifact_groups=("registries", "manifest", "markdown"),
            write=False,
            timestamp=timestamp,
        )
    )
    first_hashes = {item.relative_path: item.sha256 for item in compile_result.artifacts}
    second_hashes = {item.relative_path: item.sha256 for item in second.artifacts}
    if first_hashes != second_hashes:
        return True, False, compile_result.fingerprint, tuple(second.diagnostics)

    validation = validate_architecture(
        ValidationRequest(
            project_root=project_root,
            mode="complete",
            cross_references=True,
        )
    )
    diagnostics = tuple(compile_result.diagnostics) + tuple(validation.diagnostics)
    return True, validation.success, compile_result.fingerprint, diagnostics
