"""Private application-service adapters behind the supported SDK facade."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Literal, cast

from .. import __version__
from ..compiler import ArchitectureCompiler, CompilationMode, CompilerConfig, DiagnosticLevel
from ..compiler.driver import CompilationResult as InternalCompilationResult
from ..compiler.driver import WorkspaceCompilationResult
from ..decorators import enforces_invariant, implements_adr
from ..repository import ArchitectureRegistryError, ArchitectureRepository
from ..repository._normalized_bundle import load_normalized_bundle_from_bytes
from ..scope import ProjectScope, ProjectScopeResolver
from ..validators import ADRValidator, ValidationResult as InternalValidationResult
from ._contracts import (
    API_CONTRACT_VERSION,
    ARTIFACT_GROUPS,
    VALIDATION_MODES,
    ArtifactDescriptor,
    CapabilityManifest,
    CompilationRequest,
    CompilationResult,
    Diagnostic,
    ValidationRequest,
    ValidationResult,
    _normalize_project_root,
)
from ._errors import OperationError, RepositoryError
from ._promotion_contracts import (
    PromotionApplyRequest,
    PromotionApplyResult,
    PromotionCheckRequest,
    PromotionCheckResult,
    PromotionPrepareRequest,
    PromotionPrepareResult,
)

Severity = Literal["info", "warning", "error"]
ValidationFileResults = dict[str, InternalValidationResult]
RecursiveValidationResults = dict[str, ValidationFileResults]


def _severity(value: object) -> Severity:
    normalized = str(value)
    if normalized not in {"info", "warning", "error"}:
        raise OperationError(f"Unsupported diagnostic severity: {normalized}")
    return cast(Severity, normalized)


def _display_path(project_root: Path, value: str | Path | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _validation_diagnostic(
    request: ValidationRequest,
    item: object,
    path: str | None,
) -> Diagnostic:
    return Diagnostic(
        severity=_severity(getattr(item, "severity")),
        code=str(getattr(item, "rule")),
        message=str(getattr(item, "message")),
        path=_display_path(request.project_root, path),
        field=getattr(item, "field", None),
    )


def _compiler_diagnostic(project_root: Path, item: object) -> Diagnostic:
    level = getattr(item, "level")
    severity = {
        DiagnosticLevel.INFO: "info",
        DiagnosticLevel.WARNING: "warning",
        DiagnosticLevel.ERROR: "error",
    }[level]
    return Diagnostic(
        severity=_severity(severity),
        code=str(getattr(item, "code")),
        message=str(getattr(item, "message")),
        path=_display_path(project_root, getattr(item, "path", None)),
        source_ref=getattr(item, "source_ref", None),
    )


def _artifact_group(relative_path: str) -> str:
    if relative_path == "adrs/manifest.yaml":
        return "manifest"
    if relative_path.startswith("adrs/rendered/"):
        return "markdown"
    return "registries"


def _artifact_id(relative_path: str) -> str:
    identities = {
        "adrs/manifest.yaml": "manifest",
        "adrs/index/architecture-index.yaml": "architecture-index",
        "adrs/index/entity-registry.yaml": "entity-registry",
        "adrs/index/relationship-registry.yaml": "relationship-registry",
        "adrs/index/unresolved-registry.yaml": "unresolved-registry",
        "adrs/index/decision-registry.yaml": "decision-registry",
        "adrs/index/capability-registry.yaml": "capability-registry",
        "adrs/index/invariant-registry.yaml": "invariant-registry",
        "adrs/index/component-registry.yaml": "component-registry",
        "adrs/index/system-registry.yaml": "system-registry",
        "adrs/entities/registry.yaml": "legacy-entity-registry",
    }
    if relative_path in identities:
        return identities[relative_path]
    if relative_path.startswith("adrs/rendered/") and relative_path.endswith(".md"):
        return f"rendered-adr:{Path(relative_path).stem}"
    raise OperationError(f"Unsupported emitted artifact path: {relative_path}")


@implements_adr("ADR-L-0013", "ADR-PC-0002")
def validate_for_cli(
    scope: Path | None,
    *,
    recursive: bool,
    cross_references: bool,
    mode: str,
) -> tuple[
    ProjectScope | None,
    ValidationFileResults | RecursiveValidationResults,
    InternalValidationResult | None,
]:
    """Run the compatibility-preserved CLI validation application service."""

    resolver = ProjectScopeResolver(explicit_scope=scope)
    validator = ADRValidator(scope_resolver=resolver)
    if recursive:
        return None, validator.validate_recursive(mode=mode), None

    detected_scope = resolver.resolve()
    results = validator.validate_scope(detected_scope, mode=mode)
    cross_reference_result = (
        validator.validate_cross_references(detected_scope.adr_dir) if cross_references else None
    )
    return detected_scope, results, cross_reference_result


@implements_adr("ADR-L-0013", "ADR-PC-0003")
def compile_for_cli(
    scope: Path | None,
    *,
    emit_targets: set[str],
    timestamp: str | None,
    mode: str,
    dry_run: bool,
    check: bool,
    validate_contract: bool,
    contract_profile: str,
    recursive: bool,
) -> tuple[
    ProjectScope | None,
    InternalCompilationResult | WorkspaceCompilationResult,
]:
    """Run the compatibility-preserved CLI compilation application service."""

    resolver = ProjectScopeResolver(explicit_scope=scope)
    compiler = ArchitectureCompiler(scope_resolver=resolver)
    config = CompilerConfig(
        mode=CompilationMode(mode),
        emit=emit_targets,
        dry_run=dry_run or check,
        check=check,
        profile=contract_profile if validate_contract else None,
        pinned_timestamp=timestamp,
        metadata={"validate_contract": "true"} if validate_contract else {},
    )
    if recursive:
        return None, compiler.compile_recursive(scope, config)

    detected_scope = resolver.resolve()
    return detected_scope, compiler.compile(detected_scope, config)


@implements_adr("ADR-L-0013", "ADR-PC-0004")
def capabilities() -> CapabilityManifest:
    """Return deterministic local SDK capability metadata."""

    from ..promotion.service import PROMOTION_OPERATIONS_ADVERTISED

    operations = [
        "capabilities",
        "validate_architecture",
        "compile_architecture",
        "open_repository",
    ]
    if PROMOTION_OPERATIONS_ADVERTISED:
        operations.extend(["prepare_promotion", "check_promotion", "apply_promotion"])
    return CapabilityManifest(
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
        operations=tuple(operations),
        validation_modes=VALIDATION_MODES,
        artifact_groups=ARTIFACT_GROUPS,
        supported_adr_schema_versions=("1.0", "1.1", "1.2"),
        stable_adr_schema_versions=("1.0",),
        provisional_adr_schema_versions=("1.1", "1.2"),
        normalized_model_schema_version="1.1",
    )


def prepare_promotion(request: PromotionPrepareRequest) -> PromotionPrepareResult:
    """Prepare a Promotion Contract into bound post-images without authority writes."""

    if not isinstance(request, PromotionPrepareRequest):
        raise TypeError("request must be a PromotionPrepareRequest")
    from ..promotion.service import prepare_promotion as _prepare

    return _prepare(request)


def check_promotion(request: PromotionCheckRequest) -> PromotionCheckResult:
    """Re-evaluate promotion readiness without authority writes."""

    if not isinstance(request, PromotionCheckRequest):
        raise TypeError("request must be a PromotionCheckRequest")
    from ..promotion.service import check_promotion as _check

    return _check(request)


def apply_promotion(request: PromotionApplyRequest) -> PromotionApplyResult:
    """Dry-run or commit a locked prepared Promotion Contract."""

    if not isinstance(request, PromotionApplyRequest):
        raise TypeError("request must be a PromotionApplyRequest")
    from ..promotion.service import apply_promotion as _apply

    return _apply(request)


@implements_adr("ADR-L-0013", "ADR-PC-0002")
def validate_architecture(request: ValidationRequest) -> ValidationResult:
    """Validate one explicit repository scope into an immutable public result."""

    if not isinstance(request, ValidationRequest):
        raise TypeError("request must be a ValidationRequest")
    try:
        resolver = ProjectScopeResolver(explicit_scope=request.project_root)
        scope = resolver.resolve()
        validator = ADRValidator(
            project_root=request.project_root,
            scope_resolver=resolver,
        )
        file_results = validator.validate_directory(
            scope.adr_dir,
            scope,
            mode=request.mode,
        )
        diagnostics: list[Diagnostic] = []
        validated_files: list[str] = []
        for path, result in sorted(file_results.items()):
            display_path = _display_path(request.project_root, path)
            if display_path is None:
                continue
            validated_files.append(display_path)
            diagnostics.extend(
                _validation_diagnostic(request, item, path) for item in result.errors
            )
            diagnostics.extend(
                _validation_diagnostic(request, item, path) for item in result.warnings
            )
        if request.cross_references:
            cross_references = validator.validate_cross_references(scope.adr_dir)
            diagnostics.extend(
                _validation_diagnostic(request, item, None) for item in cross_references.errors
            )
            diagnostics.extend(
                _validation_diagnostic(request, item, None) for item in cross_references.warnings
            )
    except Exception as exc:
        raise OperationError("Validation could not complete") from exc

    error_count = sum(item.severity == "error" for item in diagnostics)
    warning_count = sum(item.severity == "warning" for item in diagnostics)
    return ValidationResult(
        request=request,
        success=error_count == 0,
        validated_files=tuple(validated_files),
        diagnostics=tuple(diagnostics),
        error_count=error_count,
        warning_count=warning_count,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )


@implements_adr("ADR-L-0013", "ADR-PC-0003", "ADR-PC-0004")
@enforces_invariant("INV-0074")
def compile_architecture(request: CompilationRequest) -> CompilationResult:
    """Compile the supported authoring groups and contain internal result types."""

    if not isinstance(request, CompilationRequest):
        raise TypeError("request must be a CompilationRequest")
    output_root = request.output_root or request.project_root
    config = CompilerConfig(
        scope_root=request.project_root,
        emit=set(request.artifact_groups),
        dry_run=not request.write,
        output_dir=output_root if request.write else None,
        pinned_timestamp=request.timestamp,
    )
    try:
        internal = ArchitectureCompiler().compile(request.project_root, config)
        diagnostics = tuple(
            _compiler_diagnostic(request.project_root, item)
            for item in internal.diagnostics.as_list()
        )
        descriptors = tuple(
            sorted(
                (
                    ArtifactDescriptor(
                        artifact_id=_artifact_id(item.path.as_posix()),
                        group=_artifact_group(item.path.as_posix()),
                        kind=item.kind,
                        relative_path=item.path.as_posix(),
                        written_path=(output_root / item.path).resolve() if request.write else None,
                        content=item.content,
                        size_bytes=len(item.content),
                        sha256=sha256(item.content).hexdigest(),
                        integrity_header=item.integrity_header,
                    )
                    for item in internal.artifacts
                ),
                key=lambda item: item.relative_path,
            )
        )
        model = None
        fingerprint = None
        if "registries" in request.artifact_groups and descriptors:
            emitted_bytes = {item.relative_path: item.content for item in descriptors}
            bundle = load_normalized_bundle_from_bytes(request.project_root, emitted_bytes)
            model = bundle.model.model_copy(deep=True)
            fingerprint = bundle.fingerprint
    except OperationError:
        raise
    except Exception as exc:
        raise OperationError("Compilation could not complete") from exc

    statistics = internal.statistics
    return CompilationResult(
        request=request,
        success=internal.success,
        partial=not internal.success and bool(descriptors),
        artifacts=descriptors,
        diagnostics=diagnostics,
        model=model,
        fingerprint=fingerprint,
        source_files=statistics.source_files,
        parse_errors=statistics.parse_errors,
        entities_extracted=statistics.entities_extracted,
        relationships_derived=statistics.relationships_derived,
        unresolved_detected=statistics.unresolved_detected,
        artifacts_emitted=statistics.artifacts_emitted,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )


@implements_adr("ADR-L-0013", "ADR-PC-0004")
def open_repository(project_root: str | Path) -> ArchitectureRepository:
    """Resolve and eagerly open the existing stable repository contract."""

    root = _normalize_project_root(project_root)
    try:
        repository = ArchitectureRepository(root)
        repository.load()
        return repository
    except ArchitectureRegistryError as exc:
        raise RepositoryError("Architecture repository could not be opened") from exc
