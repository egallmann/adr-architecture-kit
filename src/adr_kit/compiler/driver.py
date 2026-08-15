"""Unified compiler driver for architecture compilation."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import yaml

from ..decorators import embodies, implements_adr
from ..models import (
    NormalizedEntityRegistry,
    RelationshipRegistry,
    UnresolvedRegistry,
)
from ..models.v2_0 import (
    NormalizedEntityRegistryV2,
    RelationshipRegistryV2,
    UnresolvedRegistryV2,
)
from ..parser import ADRParser
from ..schema.contract_validation import validate_adr_contract_bundle
from ..scope import ProjectScope, ProjectScopeResolver
from ..validators import ADRValidator
from .backend import (
    EmittedArtifact,
    PROJECTABLE_ENTITY_TYPES,
    build_backend_emitters,
)
from .config import CompilationMode, CompilerConfig
from .diagnostics import DiagnosticLevel, DiagnosticLog
from .ir import ArchModel
from .pipeline import run_frontend_pipeline
from .frontend import CachedADRParser
from ..repository.registry_loader import load_remediation_ledger


@dataclass(frozen=True)
class OutputArtifact:
    """A single file emitted by the compiler."""

    path: Path
    content: bytes
    kind: str
    integrity_header: str | None = None
    logical_id: str | None = None


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


@dataclass(frozen=True)
class ScopedCompilationResult:
    """Compilation result for one resolved scope within a recursive run."""

    scope: ProjectScope
    result: CompilationResult


@dataclass(frozen=True)
class WorkspaceCompilationStatistics:
    """Aggregate statistics for a recursive compile invocation."""

    scopes_compiled: int
    successful_scopes: int
    failed_scopes: int
    source_files: int
    parse_errors: int
    entities_extracted: int
    relationships_derived: int
    unresolved_detected: int
    artifacts_emitted: int


@dataclass(frozen=True)
class WorkspaceCompilationResult:
    """Aggregate result returned by recursive multi-scope compilation."""

    success: bool
    scope_results: list[ScopedCompilationResult]
    artifacts: list[OutputArtifact]
    diagnostics: DiagnosticLog
    statistics: WorkspaceCompilationStatistics
    duration_ms: int


class _FixedDateTime(datetime):
    """Patch target for deterministic generator timestamps."""

    fixed_timestamp: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.fixed_timestamp.replace(tzinfo=None)
        return cls.fixed_timestamp.astimezone(tz)


@implements_adr("ADR-L-0009", "ADR-L-0013")
@embodies("019fee89-e618-7d04-9337-4aa2d3258507")
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
        timestamp, check_timestamp_error = self._resolve_generation_timestamp(resolved_scope, config)
        if check_timestamp_error is not None:
            diagnostics.error("E705", check_timestamp_error)
            duration_ms = int((perf_counter() - started) * 1000)
            empty_model = ArchModel()
            empty_model.metadata.scope_root = str(resolved_scope.root)
            return CompilationResult(
                success=False,
                artifacts=[],
                diagnostics=diagnostics,
                statistics=CompilationStatistics(
                    source_files=0,
                    parse_errors=0,
                    entities_extracted=0,
                    relationships_derived=0,
                    unresolved_detected=0,
                    artifacts_emitted=0,
                ),
                model=empty_model,
                duration_ms=duration_ms,
            )
        skip_artifact_check = False

        with self._pinned_generation_time(timestamp):
            build_result = run_frontend_pipeline(
                scope=resolved_scope,
                parser=CachedADRParser(self.parser),
                config=config,
                diagnostics=diagnostics,
            )
            model = build_result.model
            model.metadata.scope_root = str(resolved_scope.root)
            model.metadata.generated_at = timestamp or datetime.now(timezone.utc).replace(microsecond=0)

            artifacts = self._emit_artifacts(resolved_scope, config, diagnostics, build_result)

        self._validate_compile_governance_gate(resolved_scope, diagnostics)

        if config.check:
            if not skip_artifact_check:
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

    def compile_recursive(
        self,
        scope: Path | ProjectScope | None = None,
        config: CompilerConfig | None = None,
    ) -> WorkspaceCompilationResult:
        """Compile every discovered scope independently and aggregate the results."""

        started = perf_counter()
        config = config or CompilerConfig()
        root_scope = self._resolve_scope(scope, config)
        all_scopes = self.scope_resolver.resolve_recursive(root_scope.root)
        ordered_scopes = [root_scope, *sorted(
            (item for item in all_scopes if item.root != root_scope.root),
            key=lambda item: item.root.as_posix(),
        )]

        aggregate_diagnostics = DiagnosticLog()
        scope_results: list[ScopedCompilationResult] = []
        artifacts: list[OutputArtifact] = []

        for current_scope in ordered_scopes:
            try:
                result = self.compile(current_scope, config)
            except Exception as exc:
                diagnostics = DiagnosticLog()
                diagnostics.error(
                    "E799",
                    f"Scope compilation failed: {exc}",
                    path=current_scope.root,
                )
                result = CompilationResult(
                    success=False,
                    artifacts=[],
                    diagnostics=diagnostics,
                    statistics=CompilationStatistics(
                        source_files=0,
                        parse_errors=1,
                        entities_extracted=0,
                        relationships_derived=0,
                        unresolved_detected=0,
                        artifacts_emitted=0,
                    ),
                    model=ArchModel(),
                    duration_ms=0,
                )

            scope_results.append(ScopedCompilationResult(scope=current_scope, result=result))
            aggregate_diagnostics.extend(result.diagnostics.as_list())
            artifacts.extend(result.artifacts)

        duration_ms = int((perf_counter() - started) * 1000)
        successful_scopes = sum(1 for item in scope_results if item.result.success)
        failed_scopes = len(scope_results) - successful_scopes
        statistics = WorkspaceCompilationStatistics(
            scopes_compiled=len(scope_results),
            successful_scopes=successful_scopes,
            failed_scopes=failed_scopes,
            source_files=sum(item.result.statistics.source_files for item in scope_results),
            parse_errors=sum(item.result.statistics.parse_errors for item in scope_results),
            entities_extracted=sum(item.result.statistics.entities_extracted for item in scope_results),
            relationships_derived=sum(item.result.statistics.relationships_derived for item in scope_results),
            unresolved_detected=sum(item.result.statistics.unresolved_detected for item in scope_results),
            artifacts_emitted=sum(item.result.statistics.artifacts_emitted for item in scope_results),
        )
        return WorkspaceCompilationResult(
            success=all(item.result.success for item in scope_results),
            scope_results=scope_results,
            artifacts=artifacts,
            diagnostics=aggregate_diagnostics,
            statistics=statistics,
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
        entity_registry = self._parse_entity_registry_artifact(
            parser, entity_registry_artifact.content.decode("utf-8")
        )
        relationship_registry = self._parse_relationship_registry_artifact(
            parser, relationship_registry_artifact.content.decode("utf-8")
        )
        unresolved_registry = self._parse_unresolved_registry_artifact(
            parser, unresolved_registry_artifact.content.decode("utf-8")
        )

        remediation_ledger = None
        remediation_ledger_path = scope.adr_dir / "governance" / "remediation-ledger.yaml"
        if remediation_ledger_path.exists():
            remediation_ledger = load_remediation_ledger(parser, remediation_ledger_path)

        result = validate_adr_contract_bundle(
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

    @staticmethod
    def _peek_schema_version(yaml_text: str) -> str | None:
        data = yaml.safe_load(yaml_text)
        if not isinstance(data, dict):
            raise ValueError("Expected mapping for registry artifact")
        version = data.get("schema_version")
        return str(version) if version is not None else None

    @classmethod
    def _parse_entity_registry_artifact(
        cls, parser: ADRParser, yaml_text: str
    ) -> NormalizedEntityRegistry | NormalizedEntityRegistryV2:
        if cls._peek_schema_version(yaml_text) == "2.0":
            data = yaml.safe_load(yaml_text)
            return NormalizedEntityRegistryV2.model_validate(data)
        return parser.parse_normalized_entity_registry_from_data(yaml_text)

    @classmethod
    def _parse_relationship_registry_artifact(
        cls, parser: ADRParser, yaml_text: str
    ) -> RelationshipRegistry | RelationshipRegistryV2:
        if cls._peek_schema_version(yaml_text) == "2.0":
            data = yaml.safe_load(yaml_text)
            return RelationshipRegistryV2.model_validate(data)
        return parser.parse_relationship_registry_from_data(yaml_text)

    @classmethod
    def _parse_unresolved_registry_artifact(
        cls, parser: ADRParser, yaml_text: str
    ) -> UnresolvedRegistry | UnresolvedRegistryV2:
        if cls._peek_schema_version(yaml_text) == "2.0":
            data = yaml.safe_load(yaml_text)
            return UnresolvedRegistryV2.model_validate(data)
        return parser.parse_unresolved_registry_from_data(yaml_text)

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
        build_result,
    ) -> list[OutputArtifact]:
        emitted: list[EmittedArtifact] = []
        selected = set(config.emit)
        emitters = build_backend_emitters(parser=self.parser, scope=scope, build_result=build_result)
        for emitter_name in ("registries", "manifest", "markdown", "graph"):
            if emitter_name not in selected:
                continue
            emitter = emitters[emitter_name]
            emitted.extend(emitter.emit())
            diagnostics.extend(emitter.diagnostics())

        return [
            OutputArtifact(
                path=item.path,
                content=item.content,
                kind=item.kind,
                integrity_header=item.integrity_header,
                logical_id=item.logical_id,
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

    def _parse_timestamp(self, timestamp: str | datetime | None) -> datetime | None:
        if timestamp is None:
            return None
        if isinstance(timestamp, datetime):
            parsed = timestamp
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        normalized = timestamp.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _resolve_generation_timestamp(
        self,
        scope: ProjectScope,
        config: CompilerConfig,
    ) -> tuple[datetime | None, str | None]:
        explicit_timestamp = self._parse_timestamp(config.pinned_timestamp)
        if explicit_timestamp is not None:
            return explicit_timestamp, None

        root = (config.output_dir or scope.root).resolve()
        candidates: list[tuple[str, datetime]] = []

        def _load_timestamp(path: Path, field_name: str) -> tuple[datetime | None, str | None]:
            if not path.exists():
                return None, None
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or field_name not in data:
                return None, f"Compiled artifact timestamp metadata missing from {path.relative_to(root).as_posix()}"
            return self._parse_timestamp(data[field_name]), None

        if "manifest" in config.emit:
            timestamp, error = _load_timestamp(root / "adrs" / "manifest.yaml", "generated_date")
            if error is not None:
                return None, error
            if timestamp is not None:
                candidates.append(("adrs/manifest.yaml", timestamp))

        if "registries" in config.emit:
            timestamp, error = _load_timestamp(root / "adrs" / "index" / "architecture-index.yaml", "generated_at")
            if error is not None:
                return None, error
            if timestamp is not None:
                candidates.append(("adrs/index/architecture-index.yaml", timestamp))

        if not candidates:
            return None, None

        unique_timestamps = {item[1] for item in candidates}
        if len(unique_timestamps) > 1:
            mismatch = ", ".join(f"{path}={timestamp.isoformat().replace('+00:00', 'Z')}" for path, timestamp in candidates)
            return None, f"Compiled artifact timestamps disagree for deterministic check: {mismatch}"

        return candidates[0][1], None

    def _validate_compile_governance_gate(
        self,
        scope: ProjectScope,
        diagnostics: DiagnosticLog,
    ) -> None:
        validator = ADRValidator(parser=self.parser, scope_resolver=ProjectScopeResolver(explicit_scope=scope.root))
        result = validator.validate_implementation_authority_gate(scope.adr_dir)
        for error in result.errors:
            diagnostics.error("E706", error.message)

    @contextmanager
    def _pinned_generation_time(self, timestamp: datetime | None):
        if timestamp is None:
            yield
            return

        with ExitStack() as stack:
            _FixedDateTime.fixed_timestamp = timestamp
            stack.enter_context(patch("adr_kit.generators.architecture_index_generator.datetime", _FixedDateTime))
            stack.enter_context(patch("adr_kit.generators.manifest_generator.datetime", _FixedDateTime))
            stack.enter_context(patch("adr_kit.compiler.backend.manifest_rendering.datetime", _FixedDateTime))
            yield
