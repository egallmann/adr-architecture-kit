"""Unified compiler driver for architecture compilation."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from ..generators import ArchitectureIndexGenerator, ManifestGenerator
from ..generators.views import MarkdownGenerator
from ..parser import ADRParser
from ..schema.contract_validation import validate_kernel_contract_bundle
from ..scope import ProjectScope, ProjectScopeResolver
from .backend import (
    EmittedArtifact,
    PROJECTABLE_ENTITY_TYPES,
    emit_manifest_artifact,
    emit_markdown_artifacts,
    emit_registry_artifacts,
)
from .config import CompilationMode, CompilerConfig
from .diagnostics import DiagnosticLevel, DiagnosticLog
from .frontend import ArchModelBuilder
from .ir import ArchModel
from ..repository.registry_loader import load_remediation_ledger


@dataclass(frozen=True)
class OutputArtifact:
    """A single file emitted by the compiler."""

    path: Path
    content: bytes
    kind: str
    integrity_header: str | None = None


@dataclass(frozen=True)
class CompilationStatistics:
    """Summary statistics for one compile invocation."""

    source_files: int
    parse_errors: int
    entities_extracted: int
    relationships_derived: int
    unresolved_detected: int
    artifacts_emitted: int


@dataclass(frozen=True)
class CompilationResult:
    """Canonical result object returned by the unified driver."""

    success: bool
    artifacts: list[OutputArtifact]
    diagnostics: DiagnosticLog
    statistics: CompilationStatistics
    model: ArchModel
    duration_ms: int


class _FixedDateTime(datetime):
    """Patch target for deterministic generator timestamps."""

    fixed_timestamp: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.fixed_timestamp.replace(tzinfo=None)
        return cls.fixed_timestamp.astimezone(tz)


class ArchitectureCompiler:
    """Single-scope architecture compiler driver."""

    def __init__(
        self,
        *,
        scope_resolver: ProjectScopeResolver | None = None,
        parser: ADRParser | None = None,
    ) -> None:
        self.scope_resolver = scope_resolver or ProjectScopeResolver()
        self.parser = parser or ADRParser()

    def compile(
        self,
        scope: Path | ProjectScope | None = None,
        config: CompilerConfig | None = None,
    ) -> CompilationResult:
        """Compile architecture artifacts for one scope."""

        started = perf_counter()
        config = config or CompilerConfig()
        diagnostics = DiagnosticLog()
        resolved_scope = self._resolve_scope(scope, config)
        timestamp = self._parse_timestamp(config.pinned_timestamp)

        with self._pinned_generation_time(timestamp):
            builder = ArchModelBuilder(
                scope_resolver=ProjectScopeResolver(explicit_scope=resolved_scope.root),
                config=config,
                diagnostics=diagnostics,
            )
            build_result = builder.build_from_scope(resolved_scope)
            model = build_result.model
            model.metadata.scope_root = str(resolved_scope.root)
            model.metadata.generated_at = timestamp or datetime.now(timezone.utc).replace(microsecond=0)

            artifacts = self._emit_artifacts(resolved_scope, config, diagnostics)

        if config.check:
            self._check_artifacts(artifacts, resolved_scope, config, diagnostics)
        elif not config.dry_run:
            self._write_artifacts(artifacts, resolved_scope, config)

        if config.metadata.get("validate_contract") == "true":
            self._validate_contract(artifacts, resolved_scope, config, diagnostics)

        success = self._compute_success(diagnostics, config)

        duration_ms = int((perf_counter() - started) * 1000)
        projectable_entities = [
            entity for entity in build_result.model.entities.values() if entity.entity_type in PROJECTABLE_ENTITY_TYPES
        ]
        statistics = CompilationStatistics(
            source_files=len(build_result.model.corpus.artifacts),
            parse_errors=0,
            entities_extracted=len(projectable_entities),
            relationships_derived=len(build_result.model.relationships.values()),
            unresolved_detected=len(build_result.model.unresolved.values()),
            artifacts_emitted=len(artifacts),
        )
        return CompilationResult(
            success=success,
            artifacts=artifacts,
            diagnostics=diagnostics,
            statistics=statistics,
            model=build_result.model,
            duration_ms=duration_ms,
        )

    def _compute_success(self, diagnostics: DiagnosticLog, config: CompilerConfig) -> bool:
        items = diagnostics.as_list()
        if not any(item.level == DiagnosticLevel.ERROR for item in items):
            return True

        if config.mode == CompilationMode.LENIENT:
            non_lenient_errors = [
                item for item in items if item.level == DiagnosticLevel.ERROR and item.code not in {"E701", "E702", "E703", "E704"}
            ]
            return not non_lenient_errors

        return False

    def _validate_contract(
        self,
        artifacts: list[OutputArtifact],
        scope: ProjectScope,
        config: CompilerConfig,
        diagnostics: DiagnosticLog,
    ) -> None:
        artifact_map = {artifact.path.as_posix(): artifact for artifact in artifacts}
        parser = self.parser
        architecture_index_artifact = artifact_map.get("adrs/index/architecture-index.yaml")
        entity_registry_artifact = artifact_map.get("adrs/index/entity-registry.yaml")
        relationship_registry_artifact = artifact_map.get("adrs/index/relationship-registry.yaml")
        unresolved_registry_artifact = artifact_map.get("adrs/index/unresolved-registry.yaml")
        if not all((architecture_index_artifact, entity_registry_artifact, relationship_registry_artifact, unresolved_registry_artifact)):
            diagnostics.error(
                "E703",
                "Contract validation requires registries emission in the current compile invocation",
            )
            return

        architecture_index = parser.parse_architecture_index_from_data(
            architecture_index_artifact.content.decode("utf-8")
        )
        entity_registry = parser.parse_normalized_entity_registry_from_data(
            entity_registry_artifact.content.decode("utf-8")
        )
        relationship_registry = parser.parse_relationship_registry_from_data(
            relationship_registry_artifact.content.decode("utf-8")
        )
        unresolved_registry = parser.parse_unresolved_registry_from_data(
            unresolved_registry_artifact.content.decode("utf-8")
        )

        remediation_ledger = None
        remediation_ledger_path = scope.adr_dir / "governance" / "remediation-ledger.yaml"
        if remediation_ledger_path.exists():
            remediation_ledger = load_remediation_ledger(parser, remediation_ledger_path)

        result = validate_kernel_contract_bundle(
            architecture_index,
            entity_registry,
            relationship_registry,
            unresolved_registry,
            profile=config.profile or "greenfield",
            remediation_ledger=remediation_ledger,
        )
        for issue in result.issues:
            diagnostics.error("E704", issue.message, path=issue.path)
        if result.outcome == "sentinel_compliant":
            diagnostics.warning(
                "W704",
                f"Contract validation passed with sentinel-backed content under profile={result.profile}",
            )

    def _resolve_scope(self, scope: Path | ProjectScope | None, config: CompilerConfig) -> ProjectScope:
        if isinstance(scope, ProjectScope):
            return scope
        if scope is not None:
            return ProjectScopeResolver(explicit_scope=Path(scope)).resolve()
        if config.scope_root is not None:
            return ProjectScopeResolver(explicit_scope=config.scope_root).resolve()
        return self.scope_resolver.resolve()

    def _emit_artifacts(
        self,
        scope: ProjectScope,
        config: CompilerConfig,
        diagnostics: DiagnosticLog,
    ) -> list[OutputArtifact]:
        emitted: list[EmittedArtifact] = []
        selected = set(config.emit)

        if "registries" in selected:
            index_generator = ArchitectureIndexGenerator(
                parser=self.parser,
                scope_resolver=ProjectScopeResolver(explicit_scope=scope.root),
            )
            bundle = index_generator.generate_from_scope(scope)
            diagnostics.extend(index_generator.diagnostics.as_list())
            emitted.extend(
                emit_registry_artifacts(
                    bundle,
                    generator=index_generator,
                    scope=scope,
                )
            )

        if "manifest" in selected:
            manifest_generator = ManifestGenerator(
                parser=self.parser,
                scope_resolver=ProjectScopeResolver(explicit_scope=scope.root),
            )
            emitted.append(
                emit_manifest_artifact(
                    generator=manifest_generator,
                    scope=scope,
                )
            )

        if "markdown" in selected:
            emitted.extend(
                emit_markdown_artifacts(
                    parser=self.parser,
                    generator=MarkdownGenerator(),
                    scope=scope,
                )
            )

        return [
            OutputArtifact(
                path=item.path,
                content=item.content,
                kind=item.kind,
                integrity_header=item.integrity_header,
            )
            for item in emitted
        ]

    def _write_artifacts(
        self,
        artifacts: list[OutputArtifact],
        scope: ProjectScope,
        config: CompilerConfig,
    ) -> None:
        root = (config.output_dir or scope.root).resolve()
        for artifact in artifacts:
            output_path = root / artifact.path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(artifact.content)

    def _check_artifacts(
        self,
        artifacts: list[OutputArtifact],
        scope: ProjectScope,
        config: CompilerConfig,
        diagnostics: DiagnosticLog,
    ) -> None:
        root = (config.output_dir or scope.root).resolve()
        for artifact in artifacts:
            output_path = root / artifact.path
            if not output_path.exists():
                diagnostics.error("E701", f"Compiled artifact missing on disk: {artifact.path}", path=artifact.path)
                continue
            if output_path.read_bytes() != artifact.content:
                artifact_label = artifact.path.as_posix()
                diagnostics.error("E702", f"Compiled artifact drift detected: {artifact_label}", path=artifact.path)

    def _parse_timestamp(self, timestamp: str | None) -> datetime | None:
        if timestamp is None:
            return None
        normalized = timestamp.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @contextmanager
    def _pinned_generation_time(self, timestamp: datetime | None):
        if timestamp is None:
            yield
            return

        with ExitStack() as stack:
            _FixedDateTime.fixed_timestamp = timestamp
            stack.enter_context(patch("src.adr_kit.generators.architecture_index_generator.datetime", _FixedDateTime))
            stack.enter_context(patch("src.adr_kit.generators.manifest_generator.datetime", _FixedDateTime))
            yield
