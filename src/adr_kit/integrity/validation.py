"""Validation service for generated documentation artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Callable

from ..scope import ProjectScope, ProjectScopeResolver
from .artifacts import ArtifactKind, GeneratedArtifact, ScopeProjectionArtifacts
from .core import (
    IntegrityHeaderError,
    compute_rendered_hash,
    extract_body_without_header,
    parse_integrity_header,
)


class GeneratedArtifactStatus(StrEnum):
    """Validation status for generated artifacts."""

    VALID = "valid"
    STALE_GENERATED_OUTPUT = "stale_generated_output"
    TAMPERED_GENERATED_OUTPUT = "tampered_generated_output"
    MISSING_OR_MALFORMED_INTEGRITY_HEADER = "missing_or_malformed_integrity_header"
    UNSUPPORTED_ARTIFACT_KIND = "unsupported_artifact_kind"


@dataclass
class GeneratedArtifactValidationResult:
    """Structured diagnostic result for a generated artifact."""

    artifact_path: str
    artifact_kind: str
    status: str
    reason_code: str
    expected_source_hash: str | None = None
    actual_source_hash: str | None = None
    expected_rendered_hash: str | None = None
    actual_rendered_hash: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status == GeneratedArtifactStatus.VALID.value


class GeneratedArtifactValidator:
    """Validate covered generated artifacts for one or more scopes."""

    def __init__(
        self,
        inspector: Callable[[GeneratedArtifact], tuple[str, list[Path], object]] | None = None,
        scope_resolver: ProjectScopeResolver | None = None,
    ):
        from ..projection import ProjectionInspector

        self.projection_inspector = ProjectionInspector()
        self.inspector = inspector or self.projection_inspector.inspect
        self.scope_resolver = scope_resolver or ProjectScopeResolver()

    def enumerate_scope_artifacts(self, scope: ProjectScope) -> list[GeneratedArtifact]:
        rendered_dir = scope.adr_dir / "rendered"
        artifacts: list[GeneratedArtifact] = []
        if scope.manifest_path.exists():
            artifacts.append(GeneratedArtifact(scope.manifest_path, ArtifactKind.MANIFEST, scope))
        system_overview_path = scope.root / "SYSTEM-OVERVIEW.md"
        if system_overview_path.exists():
            artifacts.append(GeneratedArtifact(system_overview_path, ArtifactKind.SYSTEM_OVERVIEW, scope))
        for path in sorted(rendered_dir.glob("*.md")) if rendered_dir.exists() else []:
            if path.is_file() and not path.is_symlink():
                artifacts.append(GeneratedArtifact(path, ArtifactKind.RENDERED_ADR_MARKDOWN, scope))
        return artifacts

    def validate_artifact(self, artifact: GeneratedArtifact) -> GeneratedArtifactValidationResult:
        artifact_path = artifact.artifact_path
        if not artifact_path.exists():
            return GeneratedArtifactValidationResult(
                artifact_path=str(artifact_path),
                artifact_kind=artifact.artifact_kind.value,
                status=GeneratedArtifactStatus.MISSING_OR_MALFORMED_INTEGRITY_HEADER.value,
                reason_code="artifact_missing",
                notes=["Generated artifact file does not exist."],
            )

        actual = artifact_path.read_text(encoding="utf-8")
        try:
            header = parse_integrity_header(actual, artifact.artifact_kind)
        except IntegrityHeaderError as exc:
            return GeneratedArtifactValidationResult(
                artifact_path=str(artifact_path),
                artifact_kind=artifact.artifact_kind.value,
                status=GeneratedArtifactStatus.MISSING_OR_MALFORMED_INTEGRITY_HEADER.value,
                reason_code="malformed_header",
                notes=[str(exc)],
            )

        body = extract_body_without_header(actual)
        actual_rendered_hash = compute_rendered_hash(body)
        if header["artifact_kind"] not in {kind.value for kind in ArtifactKind}:
            return GeneratedArtifactValidationResult(
                artifact_path=str(artifact_path),
                artifact_kind=header["artifact_kind"],
                status=GeneratedArtifactStatus.UNSUPPORTED_ARTIFACT_KIND.value,
                reason_code="unsupported_artifact_kind",
            )

        expected_body, source_inputs, generator_identity = self.inspector(artifact)
        expected_source_hash = self.projection_inspector.compute_source_hash(
            artifact.scope.root,
            source_inputs,
            generator_identity,
        )
        expected_rendered_hash = compute_rendered_hash(expected_body)

        if actual_rendered_hash != header["rendered_hash"]:
            return GeneratedArtifactValidationResult(
                artifact_path=str(artifact_path),
                artifact_kind=artifact.artifact_kind.value,
                status=GeneratedArtifactStatus.TAMPERED_GENERATED_OUTPUT.value,
                reason_code="rendered_hash_mismatch",
                expected_source_hash=expected_source_hash,
                actual_source_hash=header["source_hash"],
                expected_rendered_hash=expected_rendered_hash,
                actual_rendered_hash=actual_rendered_hash,
            )

        if expected_source_hash != header["source_hash"]:
            return GeneratedArtifactValidationResult(
                artifact_path=str(artifact_path),
                artifact_kind=artifact.artifact_kind.value,
                status=GeneratedArtifactStatus.STALE_GENERATED_OUTPUT.value,
                reason_code="source_hash_mismatch",
                expected_source_hash=expected_source_hash,
                actual_source_hash=header["source_hash"],
                expected_rendered_hash=expected_rendered_hash,
                actual_rendered_hash=actual_rendered_hash,
            )

        return GeneratedArtifactValidationResult(
            artifact_path=str(artifact_path),
            artifact_kind=artifact.artifact_kind.value,
            status=GeneratedArtifactStatus.VALID.value,
            reason_code="hashes_match",
            expected_source_hash=expected_source_hash,
            actual_source_hash=header["source_hash"],
            expected_rendered_hash=expected_rendered_hash,
            actual_rendered_hash=actual_rendered_hash,
        )

    def validate_scope(self, scope: ProjectScope) -> list[GeneratedArtifactValidationResult]:
        return [self.validate_artifact(artifact) for artifact in self.enumerate_scope_artifacts(scope)]

    def validate_recursive(self, start_dir: Path | None = None) -> dict[str, list[GeneratedArtifactValidationResult]]:
        scopes = self.scope_resolver.resolve_recursive(start_dir)
        return {scope.name or str(scope.root): self.validate_scope(scope) for scope in scopes}
