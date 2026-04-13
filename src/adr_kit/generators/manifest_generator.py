"""Manifest generator compatibility wrapper."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import patch

from ..compiler.backend.manifest_rendering import (
    MANIFEST_GENERATOR_IDENTITY,
    build_manifest_from_directory,
    build_manifest_integrity_header,
    discover_manifest_adr_files,
    discover_manifest_source_inputs,
    relative_manifest_path,
    render_manifest_for_scope as render_compiler_manifest_for_scope,
    render_manifest_yaml as render_compiler_manifest_yaml,
)
from ..decorators import implements_adr
from ..integrity import GeneratorIdentity
from ..models import Manifest
from ..parser import ADRParser
from ..scope import ProjectScope, ProjectScopeResolver


@implements_adr("ADR-L-0009", "ADR-L-0010", "ADR-PC-0001")
class ManifestGenerator:
    """Generate manifest artifacts while delegating rendering authority to the compiler."""

    generator_identity = GeneratorIdentity(
        MANIFEST_GENERATOR_IDENTITY.generator_id,
        MANIFEST_GENERATOR_IDENTITY.generator_version,
    )

    def __init__(self, parser: ADRParser = None, scope_resolver: ProjectScopeResolver = None):
        self.parser = parser or ADRParser()
        self.scope_resolver = scope_resolver or ProjectScopeResolver()

    def _discover_adr_files(self, adr_dir: Path) -> Tuple[List[Path], List[Path]]:
        return discover_manifest_adr_files(adr_dir)

    def _relative_manifest_path(self, file_path: Path, adr_dir: Path) -> str:
        return relative_manifest_path(file_path, adr_dir)

    def generate_from_directory(self, adr_dir: Path, scope: Optional[ProjectScope] = None) -> Manifest:
        with patch("src.adr_kit.compiler.backend.manifest_rendering.datetime", datetime):
            return build_manifest_from_directory(
                adr_dir,
                parser=self.parser,
                scope=scope,
                scope_resolver=self.scope_resolver,
            )

    def discover_source_inputs(self, adr_dir: Path) -> List[Path]:
        return discover_manifest_source_inputs(adr_dir)

    def render_manifest_yaml(self, manifest: Manifest) -> str:
        return render_compiler_manifest_yaml(manifest)

    def render_for_scope(self, scope: ProjectScope) -> tuple[str, List[Path]]:
        with patch("src.adr_kit.compiler.backend.manifest_rendering.datetime", datetime):
            return render_compiler_manifest_for_scope(
                parser=self.parser,
                scope=scope,
                scope_resolver=self.scope_resolver,
            )

    def build_integrity_header(self, scope: ProjectScope, body: str, source_inputs: List[Path]) -> str:
        return build_manifest_integrity_header(scope, body, source_inputs)

    def generate_from_scope(self, scope: Optional[ProjectScope] = None) -> Manifest:
        if scope is None:
            scope = self.scope_resolver.resolve()
        return self.generate_from_directory(scope.adr_dir, scope)

    def generate_recursive(self, scope: Optional[ProjectScope] = None) -> Dict[str, Manifest]:
        if scope is None:
            scope = self.scope_resolver.resolve()

        manifests: Dict[str, Manifest] = {}
        for current_scope in self.scope_resolver.resolve_recursive(scope.root):
            if not current_scope.adr_dir.exists():
                continue
            try:
                manifests[current_scope.name or str(current_scope.root)] = self.generate_from_directory(
                    current_scope.adr_dir,
                    current_scope,
                )
            except Exception as exc:
                print(f"Warning: Failed to generate manifest for {current_scope.name}: {exc}")
        return manifests

    def _slugify(self, text: str) -> str:
        return text.lower().replace(" ", "-").replace(":", "")[:50]

    def save_manifest(self, manifest: Manifest, output_path: Path, scope: ProjectScope | None = None):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        scope = scope or self.scope_resolver.resolve(output_path.parent)
        body = self.render_manifest_yaml(manifest)
        source_inputs = self.discover_source_inputs(scope.adr_dir)
        header = self.build_integrity_header(scope, body, source_inputs)
        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(header)
            handle.write(body)
