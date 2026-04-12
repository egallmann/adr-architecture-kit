"""Validator for generated SYSTEM-OVERVIEW.md artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from ..decorators import enforces_invariant, implements_adr
from ..integrity import GeneratedArtifactValidator, GeneratedArtifactStatus
from ..integrity.artifacts import ArtifactKind, GeneratedArtifact
from ..integrity.core import extract_body_without_header
from ..generators.system_overview_generator import SystemOverviewGenerator
from ..scope import ProjectScopeResolver


@dataclass
class SystemOverviewValidationResult:
    """Validation result for SYSTEM-OVERVIEW.md."""

    errors: List[str]
    warnings: List[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


@implements_adr("ADR-L-0007", "ADR-PC-0005")
@enforces_invariant("INV-0037", "INV-0038", "INV-0039")
class SystemOverviewValidator:
    """Validate that SYSTEM-OVERVIEW.md is generated and current."""

    REQUIRED_TOKENS = [
        "document_type: system-overview",
        "audience: ai-first",
        "generation_rule:",
        "# SYSTEM-OVERVIEW",
        "## First Discovery Order",
        "`adr generate-system-overview`",
        "`adr validate-system-overview`",
    ]

    def __init__(self, generator: SystemOverviewGenerator | None = None):
        self.generator = generator or SystemOverviewGenerator()
        self.scope_resolver = ProjectScopeResolver(explicit_scope=self.generator.repo_root)
        self.generated_validator = GeneratedArtifactValidator()

    def validate_file(self, file_path: Path) -> SystemOverviewValidationResult:
        """Validate the overview file against generated content and required markers."""
        file_path = Path(file_path)
        errors: List[str] = []
        warnings: List[str] = []

        if not file_path.exists():
            return SystemOverviewValidationResult(
                errors=[f"System overview file not found: {file_path}"],
                warnings=[],
            )

        actual = file_path.read_text(encoding="utf-8")
        expected = self.generator.render()

        scope = self.scope_resolver.resolve(self.generator.repo_root)
        integrity_result = self.generated_validator.validate_artifact(
            GeneratedArtifact(file_path, ArtifactKind.SYSTEM_OVERVIEW, scope)
        )
        if integrity_result.status != GeneratedArtifactStatus.VALID.value:
            errors.append(
                f"SYSTEM-OVERVIEW.md integrity validation failed: {integrity_result.status}"
            )

        try:
            actual_body = extract_body_without_header(actual)
        except Exception:
            actual_body = actual

        if actual_body != expected:
            errors.append(
                "SYSTEM-OVERVIEW.md is stale or manually edited; regenerate it with `adr generate-system-overview`."
            )

        if actual_body.startswith("---\n"):
            errors.append(
                "SYSTEM-OVERVIEW.md still uses visible YAML frontmatter; regenerate it with the hidden metadata format."
            )

        for token in self.REQUIRED_TOKENS:
            if token not in actual:
                errors.append(f"Missing required overview token: {token}")

        if "\r\n" in actual:
            warnings.append("SYSTEM-OVERVIEW.md uses CRLF line endings; LF is preferred for stable generation.")

        return SystemOverviewValidationResult(errors=errors, warnings=warnings)
