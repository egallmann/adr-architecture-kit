"""Generated artifact metadata and scope discovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ..scope import ProjectScope


class ArtifactKind(StrEnum):
    """Supported generated artifact kinds."""

    MANIFEST = "manifest"
    LEGACY_ENTITY_REGISTRY = "legacy_entity_registry"
    RENDERED_ADR_MARKDOWN = "rendered_adr_markdown"
    SYSTEM_OVERVIEW = "system_overview"


@dataclass(frozen=True)
class GeneratedArtifact:
    """A concrete generated artifact within a scope."""

    artifact_path: Path
    artifact_kind: ArtifactKind
    scope: ProjectScope


@dataclass(frozen=True)
class ScopeProjectionArtifacts:
    """Known generated artifacts for a project scope."""

    scope: ProjectScope
    manifest_path: Path
    legacy_entity_registry_path: Path
    rendered_dir: Path
    system_overview_path: Path
