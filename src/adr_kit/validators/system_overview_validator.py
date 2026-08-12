"""Validator for generated SYSTEM-OVERVIEW.md artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from ..decorators import enforces_invariant, implements_adr
from ..generators.system_overview_generator import SystemOverviewGenerator
from ..integrity import GeneratedArtifactStatus, GeneratedArtifactValidator
from ..integrity.artifacts import ArtifactKind, GeneratedArtifact
from ..integrity.core import extract_body_without_header
from ..scope import ProjectScopeResolver


@dataclass
class SystemOverviewValidationResult:
    """Validation result for SYSTEM-OVERVIEW.md."""

    errors: List[str]
    warnings: List[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


COMMON_REQUIRED_TOKENS = [
    "document_type: system-overview",
    "audience: ai-first",
    "generation_rule:",
    "# SYSTEM-OVERVIEW",
    "## Start Here",
    "## One-Line Orientation",
    "`adr generate-system-overview`",
    "`adr validate-system-overview`",
]

PROFILE_REQUIRED_TOKENS = {
    "adr-architecture-kit": [
        "## What ADR Kit Is",
        "## Supported Consumer Surfaces",
        "adr_kit.api",
        "## Authority Anchors",
        "## How to Enter for Common Tasks",
    ],
    "ste-runtime": [
        "## What ste-runtime Is",
        "implements STE runtime workflows",
        "## How to Enter for Common Tasks",
    ],
    "legacy-generic": [
        "## Compatibility Orientation",
        "## How to Enter for Common Tasks",
    ],
}

PROFILE_FORBIDDEN_TOKENS = {
    "adr-architecture-kit": [
        "documentation-state toolkit",
        "## First Discovery Order",
    ],
    "ste-runtime": [
        "adr_kit.api",
        "## First Discovery Order",
        "documentation-state toolkit",
        "src/adr_kit/",
        "## Supported Consumer Surfaces",
    ],
    "legacy-generic": [
        "adr_kit.api",
        "documentation-state toolkit",
        "## First Discovery Order",
        "src/adr_kit/",
        "## Supported Consumer Surfaces",
        "## What ADR Kit Is",
    ],
}


@implements_adr("ADR-L-0007")
@enforces_invariant("INV-0037", "INV-0038", "INV-0039", "INV-0101", "INV-0102")
class SystemOverviewValidator:
    """Validate that SYSTEM-OVERVIEW.md is generated and current."""

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
        model = self.generator.build_model()
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

        for token in COMMON_REQUIRED_TOKENS:
            if token not in actual:
                errors.append(f"Missing required overview token: {token}")

        profile_kind = model.profile.profile_kind
        for token in PROFILE_REQUIRED_TOKENS.get(profile_kind, ()):
            if token not in actual:
                errors.append(f"Missing required {profile_kind} overview token: {token}")

        for token in PROFILE_FORBIDDEN_TOKENS.get(profile_kind, ()):
            if token in actual:
                errors.append(f"Forbidden {profile_kind} overview token present: {token}")

        if "\r\n" in actual:
            warnings.append(
                "SYSTEM-OVERVIEW.md uses CRLF line endings; LF is preferred for stable generation."
            )

        return SystemOverviewValidationResult(errors=errors, warnings=warnings)
