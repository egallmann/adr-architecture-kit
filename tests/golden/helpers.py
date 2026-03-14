from __future__ import annotations

import shutil
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src.adr_kit.generators.architecture_index_generator import ArchitectureIndexGenerator
from src.adr_kit.generators.manifest_generator import ManifestGenerator
from src.adr_kit.scope import ProjectScopeResolver


FIXED_TIMESTAMP = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
GOLDEN_KEYS = (
    "architecture_index",
    "entity_registry",
    "relationship_registry",
    "unresolved_registry",
    "decision_registry",
    "capability_registry",
    "invariant_registry",
    "component_registry",
    "system_registry",
    "legacy_entity_registry",
    "manifest",
)


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return FIXED_TIMESTAMP.replace(tzinfo=None)
        return FIXED_TIMESTAMP.astimezone(tz)


def clone_scope_sources(source_root: Path, destination_root: Path) -> None:
    """Copy the minimal canonical source tree for deterministic generation."""
    source_root = source_root.resolve()
    destination_root = destination_root.resolve()
    destination_root.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_root / "PROJECT.yaml", destination_root / "PROJECT.yaml")
    for relative in (
        Path("adrs") / "logical",
        Path("adrs") / "physical",
        Path("adrs") / "physical-system",
        Path("adrs") / "physical-component",
        Path("adrs") / "invariants",
        Path("adrs") / "requirements" / "snapshots",
        Path("adrs") / "decisions" / "ledgers",
    ):
        source_dir = source_root / relative
        if source_dir.exists():
            shutil.copytree(source_dir, destination_root / relative)


@contextmanager
def pinned_generation_time():
    """Pin generator timestamps for deterministic output."""
    with ExitStack() as stack:
        stack.enter_context(patch("src.adr_kit.generators.architecture_index_generator.datetime", _FixedDateTime))
        stack.enter_context(patch("src.adr_kit.generators.manifest_generator.datetime", _FixedDateTime))
        yield


def generate_deterministic_outputs(source_root: Path, workspace_root: Path) -> dict[str, Path]:
    """Generate the current artifact set from canonical sources into a temp scope."""
    clone_scope_sources(source_root, workspace_root)
    resolver = ProjectScopeResolver(explicit_scope=workspace_root)
    scope = resolver.resolve()

    with pinned_generation_time():
        index_generator = ArchitectureIndexGenerator(scope_resolver=resolver)
        bundle = index_generator.generate_from_scope(scope)
        paths = index_generator.save_bundle(bundle, scope)

        manifest_generator = ManifestGenerator(scope_resolver=resolver)
        manifest = manifest_generator.generate_from_scope(scope)
        manifest_generator.save_manifest(manifest, scope.manifest_path, scope)
        paths["manifest"] = scope.manifest_path

    return paths
