"""Private application-service adapters behind the supported SDK facade."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping, cast

import yaml

from .. import __version__
from ..compatibility import load_host_capabilities_snapshot
from ..compiler import ArchitectureCompiler, CompilationMode, CompilerConfig, DiagnosticLevel
from ..compiler.driver import CompilationResult as InternalCompilationResult
from ..compiler.driver import WorkspaceCompilationResult
from ..core import (
    execute_architecture_validation,
    execute_architecture_reference_validation,
    execute_contract_validation,
    execute_project_metadata_validation,
    execute_provider_registry,
    execute_repository_validation,
)
from ..decorators import enforces_invariant, implements_adr
from ..repository import (
    ArchitectureRegistryError,
    ArchitectureRepository,
    ProviderBinding,
    ProviderRegistry,
)
from ..repository._normalized_bundle import load_normalized_bundle_from_bytes
from ..integrity import GeneratedArtifactStatus, GeneratedArtifactValidator
from ..parser import ADRParseError, ADRSchemaValidationError
from ..schema.contract_validation import (
    ContractProfile,
    ContractValidationIssue as InternalContractValidationIssue,
    ContractValidationResult as InternalContractValidationResult,
    ContractValidationOutcome,
)
from ..scope import ProjectScope, ProjectScopeResolver
from ..validators import (
    ADRValidator,
    ValidationError as InternalValidationError,
    ValidationResult as InternalValidationResult,
)
from ._contracts import (
    API_CONTRACT_VERSION,
    ARTIFACT_GROUPS,
    PROMOTION_CONTRACT_VERSIONS,
    VALIDATION_MODES,
    ArtifactDescriptor,
    CapabilityManifest,
    CompilationRequest,
    CompilationResult,
    ContractValidationIssue,
    ContractValidationRequest,
    ContractValidationResult,
    Diagnostic,
    GeneratedArtifactValidation,
    GeneratedDocsValidationRequest,
    GeneratedDocsValidationResult,
    ProjectMetadataValidationRequest,
    ProjectMetadataValidationResult,
    ValidationRequest,
    ValidationResult,
    _normalize_project_root,
)
from ._errors import InvalidRequestError, OperationError, RepositoryError
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


def _contract_validation_for_repository(
    repository: ArchitectureRepository,
    *,
    profile: ContractProfile,
    max_sentinel_fields: int | None,
    max_non_complete_entities: int | None,
) -> tuple[InternalContractValidationResult, bool, bool]:
    """Run the shared validator and compatibility-preserved threshold rules."""

    contract_bundle = repository.get_contract_bundle_view()
    core_result = execute_contract_validation(
        profile=profile,
        entity_registry=contract_bundle.entity_registry,
        remediation_ledger=contract_bundle.remediation_ledger,
        max_sentinel_fields=max_sentinel_fields,
        max_non_complete_entities=max_non_complete_entities,
    )
    issues = tuple(
        InternalContractValidationIssue(path=str(issue["path"]), message=str(issue["message"]))
        for issue in core_result.get("issues", [])
    )
    result = InternalContractValidationResult(
        profile=cast(ContractProfile, core_result["profile"]),
        outcome=cast(ContractValidationOutcome, core_result["outcome"]),
        issues=issues,
        sentinel_field_count=int(core_result["sentinel_field_count"]),
        non_complete_entity_count=int(core_result["non_complete_entity_count"]),
        completeness_counts={
            str(key): int(value)
            for key, value in dict(core_result.get("completeness_counts", {})).items()
        },
    )
    threshold_codes = {
        str(item.get("code"))
        for item in core_result.get("diagnostics", [])
        if isinstance(item, dict)
    }
    return (
        result,
        "contract.max_sentinel_fields" in threshold_codes,
        "contract.max_non_complete_entities" in threshold_codes,
    )


def _threshold_diagnostics(
    result: InternalContractValidationResult,
    *,
    max_sentinel_fields: int | None,
    max_non_complete_entities: int | None,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    if max_sentinel_fields is not None and result.sentinel_field_count > max_sentinel_fields:
        diagnostics.append(
            Diagnostic(
                severity="error",
                code="contract.max_sentinel_fields",
                message=(
                    f"sentinel_field_count={result.sentinel_field_count} exceeds "
                    f"max_sentinel_fields={max_sentinel_fields}"
                ),
            )
        )
    if (
        max_non_complete_entities is not None
        and result.non_complete_entity_count > max_non_complete_entities
    ):
        diagnostics.append(
            Diagnostic(
                severity="error",
                code="contract.max_non_complete_entities",
                message=(
                    f"non_complete_entity_count={result.non_complete_entity_count} exceeds "
                    f"max_non_complete_entities={max_non_complete_entities}"
                ),
            )
        )
    return tuple(diagnostics)


def _artifact_group(relative_path: str) -> str:
    if relative_path == "adrs/manifest.yaml":
        return "manifest"
    if relative_path == "SYSTEM-OVERVIEW.md":
        return "markdown"
    if relative_path.startswith("adrs/rendered/") or relative_path.startswith(
        "adrs/adr-projection/"
    ):
        return "markdown"
    return "registries"


def _artifact_id(relative_path: str, *, logical_id: str | None = None) -> str:
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
        "SYSTEM-OVERVIEW.md": "system-overview",
    }
    if relative_path in identities:
        return identities[relative_path]
    if relative_path.startswith("adrs/adr-projection/") and relative_path.endswith(".md"):
        if not logical_id:
            raise OperationError(
                f"Markdown projection artifact missing logical_id for path: {relative_path}"
            )
        return f"rendered-adr:{logical_id}"
    if relative_path.startswith("adrs/rendered/") and relative_path.endswith(".md"):
        return f"rendered-adr:{Path(relative_path).stem}"
    raise OperationError(f"Unsupported emitted artifact path: {relative_path}")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({item for item in value if isinstance(item, str)})


def _architecture_reference_facts(
    adr_dir: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    """Normalize source references before shared semantic validation."""

    source_paths: list[Path] = []
    for directory_name in ("logical", "physical", "physical-system", "physical-component"):
        directory = adr_dir / directory_name
        if directory.is_dir():
            source_paths.extend(directory.glob("*.yaml"))

    records: list[dict[str, object]] = []
    for path in sorted({item.resolve() for item in source_paths}):
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError(f"ADR source must be a mapping: {path}")
        identifier = payload.get("id")
        kind = payload.get("adr_type")
        if not isinstance(identifier, str) or not isinstance(kind, str):
            raise ValueError(f"ADR source must contain id and adr_type: {path}")
        governance = payload.get("governance")
        governance_mapping = governance if isinstance(governance, Mapping) else {}
        record: dict[str, object] = {
            "id": identifier,
            "kind": kind,
            "schema_version": str(payload.get("schema_version", "")),
            "implements_logical": _string_list(payload.get("implements_logical")),
            "implements_system": _string_list(payload.get("implements_system")),
            "references_components": _string_list(payload.get("references_components")),
            "related_adrs": _string_list(payload.get("related_adrs")),
            "related_reviews": _string_list(governance_mapping.get("related_reviews")),
            "related_overrides": _string_list(governance_mapping.get("related_overrides")),
        }
        if kind == "physical-system":
            system = payload.get("system")
            if isinstance(system, Mapping) and isinstance(system.get("id"), str):
                record["system_id"] = system["id"]
            topology = payload.get("component_topology")
            if isinstance(topology, list):
                record["topology_components"] = sorted(
                    {
                        item["component_ref"]
                        for item in topology
                        if isinstance(item, Mapping) and isinstance(item.get("component_ref"), str)
                    }
                )
        if kind == "physical-component":
            specifications = payload.get("component_specifications")
            if isinstance(specifications, list):
                record["component_specifications"] = [
                    dict(item) for item in specifications if isinstance(item, Mapping)
                ]
        records.append(record)

    def load_artifacts(directory_name: str, target_key: str) -> list[dict[str, object]]:
        directory = adr_dir / "decisions" / directory_name
        artifacts: list[dict[str, object]] = []
        if not directory.is_dir():
            return artifacts
        for path in sorted(directory.glob("*.yaml")):
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError(f"Governance artifact must be a mapping: {path}")
            identifier = payload.get("id")
            target = payload.get(target_key)
            if isinstance(identifier, str) and isinstance(target, str):
                artifacts.append(
                    {
                        "id": identifier,
                        target_key: target,
                        "related_adr_version": payload.get("related_adr_version"),
                    }
                )
        return artifacts

    return (
        records,
        load_artifacts("reviews", "target_adr"),
        load_artifacts("overrides", "related_adr"),
    )


def _shared_architecture_reference_result(adr_dir: Path) -> InternalValidationResult:
    try:
        records, reviews, overrides = _architecture_reference_facts(adr_dir)
    except (OSError, UnicodeError, TypeError, ValueError, yaml.YAMLError) as exc:
        # Source discovery/normalization is a host responsibility. Once it
        # fails, report a deterministic host diagnostic; never reactivate the
        # legacy Python cross-reference evaluator as a semantic fallback.
        return InternalValidationResult(
            valid=False,
            mode="complete",
            errors=[
                InternalValidationError(
                    severity="error",
                    rule="parse_error",
                    message=f"Cross-reference source normalization failed: {exc}",
                )
            ],
            warnings=[],
        )
    result = execute_architecture_reference_validation(
        records=records,
        reviews=reviews,
        overrides=overrides,
    )
    errors: list[InternalValidationError] = []
    warnings: list[InternalValidationError] = []
    for item in result.get("diagnostics", []):
        if not isinstance(item, Mapping):
            continue
        finding = InternalValidationError(
            severity=_severity(item.get("severity")),
            rule=str(item.get("code", "cross_reference")),
            message=str(item.get("message", "architecture reference validation failed")),
            field=str(item["path"]) if item.get("path") is not None else None,
        )
        (warnings if finding.severity == "warning" else errors).append(finding)
    return InternalValidationResult(
        valid=bool(result.get("success", False)),
        mode="complete",
        errors=errors,
        warnings=warnings,
    )


def _missing_implementation_identifiers(
    project_root: Path, document: Mapping[str, object]
) -> list[str]:
    """Normalize host filesystem facts used by the shared ADR rule evaluator."""

    missing: list[str] = []
    specifications = document.get("component_specifications")
    if not isinstance(specifications, list):
        return missing
    for specification in specifications:
        if not isinstance(specification, Mapping):
            continue
        identifiers = specification.get("implementation_identifiers")
        if not isinstance(identifiers, list):
            continue
        for identifier in identifiers:
            if not isinstance(identifier, str) or (
                "/" not in identifier and "\\" not in identifier
            ):
                continue
            if not (project_root / identifier).exists():
                missing.append(identifier)
    return sorted(set(missing))


def _shared_architecture_file_results(
    request: ValidationRequest,
    scope: ProjectScope,
    validator: ADRValidator,
) -> ValidationFileResults:
    """Parse/schema-check ADR sources, then delegate business rules to core."""

    logical_files, physical_files = validator._discover_adr_files(scope.adr_dir)
    source_paths = sorted({path.resolve() for path in logical_files + physical_files})
    file_results: ValidationFileResults = {}
    records: list[dict[str, object]] = []

    for path in source_paths:
        errors: list[InternalValidationError] = []
        warnings: list[InternalValidationError] = []
        try:
            raw_data = validator.parser.parse_yaml(path)
            if request.mode == "structural":
                validator.parser.validate_against_schema(
                    raw_data,
                    validator._schema_name_for_data(raw_data),
                    mode="structural",
                )
            else:
                # parse_adr performs the version-aware schema dispatch and host
                # model construction without executing the business rules.
                validator.parser.parse_adr(path)
        except ADRSchemaValidationError as exc:
            errors.append(
                InternalValidationError(
                    severity="error", rule="schema_validation", message=str(exc)
                )
            )
        except ADRParseError as exc:
            errors.append(
                InternalValidationError(severity="error", rule="parse_error", message=str(exc))
            )
        except Exception as exc:  # preserve the established public containment boundary
            errors.append(
                InternalValidationError(
                    severity="error", rule="unknown_error", message=f"Unexpected error: {exc}"
                )
            )
        file_results[str(path)] = InternalValidationResult(
            valid=not errors,
            mode=request.mode,
            errors=errors,
            warnings=warnings,
        )
        if errors:
            continue

        normalized = dict(raw_data)
        normalized["missing_implementation_identifiers"] = _missing_implementation_identifiers(
            request.project_root, raw_data
        )
        records.append({"path": path.as_posix(), "document": normalized})

    if request.mode == "complete" and records:
        core_result = execute_architecture_validation(records=records, mode=request.mode)
        for item in core_result.get("diagnostics", []):
            if not isinstance(item, Mapping):
                continue
            source_ref = str(item.get("source_ref", ""))
            result = file_results.get(str(Path(source_ref)))
            if result is None:
                result = file_results.get(source_ref)
            if result is None:
                continue
            finding = InternalValidationError(
                severity=_severity(item.get("severity")),
                rule=str(item.get("code", "architecture")),
                message=str(item.get("message", "architecture validation failed")),
                field=str(item["path"]) if item.get("path") is not None else None,
            )
            if finding.severity == "warning":
                result.warnings.append(finding)
            else:
                result.errors.append(finding)
            result.valid = not result.errors

    return file_results


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
    # Keep the CLI as a presentation adapter while sending its non-recursive
    # validation through the same host-normalization/shared-core path as the
    # public SDK. Recursive validation remains staged until recursive source
    # discovery and aggregation have an equivalent shared contract.
    results = _shared_architecture_file_results(
        ValidationRequest(
            project_root=detected_scope.root,
            mode=mode,  # type: ignore[arg-type]
            cross_references=False,
        ),
        detected_scope,
        validator,
    )
    if cross_references:
        cross_reference_result = _shared_architecture_reference_result(detected_scope.adr_dir)
    else:
        cross_reference_result = None
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

    contract = load_host_capabilities_snapshot()
    operations = [
        "capabilities",
        "validate_architecture",
        "validate_project_metadata",
        "validate_contract",
        "validate_generated_docs",
        "compile_architecture",
        "open_repository",
        "open_provider_registry",
        "build_embodiment_linkage",
        "generate_attribution_shim",
        "list_semantic_contracts",
        "get_semantic_contract",
        "canonicalize_semantic_json",
        "calculate_semantic_contract_fingerprint",
        "validate_semantic_resource_closure",
        "compose_semantic_contract_set",
    ]
    if PROMOTION_OPERATIONS_ADVERTISED:
        operations.extend(["prepare_promotion", "check_promotion", "apply_promotion"])
    return CapabilityManifest(
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
        operations=tuple(operations),
        supported_promotion_contract_versions=PROMOTION_CONTRACT_VERSIONS,
        validation_modes=VALIDATION_MODES,
        artifact_groups=ARTIFACT_GROUPS,
        supported_adr_schema_versions=("1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6"),
        stable_adr_schema_versions=("1.0",),
        provisional_adr_schema_versions=("1.1", "1.2", "1.3", "1.4", "1.5", "1.6"),
        normalized_model_schema_version="1.1",
        supported_normalized_model_schema_versions=("1.1", "2.0", "2.1", "2.2", "2.3"),
        supported_evidence_attribution_versions=("1.5", "1.6"),
        preferred_evidence_attribution_version="1.6",
        host_operations=tuple(str(item) for item in contract["peer_host_operations"]),
        pending_host_operations=tuple(str(item) for item in contract["pending_host_operations"]),
        browser_operations=tuple(str(item) for item in contract["browser_operations"]),
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
        file_results = _shared_architecture_file_results(request, scope, validator)
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
            cross_reference_result = _shared_architecture_reference_result(scope.adr_dir)
            diagnostics.extend(
                _validation_diagnostic(request, item, None)
                for item in cross_reference_result.errors
            )
            diagnostics.extend(
                _validation_diagnostic(request, item, None)
                for item in cross_reference_result.warnings
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


def validate_project_metadata(
    request: ProjectMetadataValidationRequest,
) -> ProjectMetadataValidationResult:
    """Validate one PROJECT.yaml through the shared semantic core."""

    if not isinstance(request, ProjectMetadataValidationRequest):
        raise InvalidRequestError("request must be a ProjectMetadataValidationRequest")
    try:
        core_result = execute_project_metadata_validation(request.project_root)
    except Exception as exc:
        raise OperationError("Project metadata validation could not complete") from exc
    diagnostics = tuple(
        Diagnostic(
            severity=_severity(item.get("severity")),
            code=str(item.get("code", "project_metadata.invalid")),
            message=str(item.get("message", "project metadata validation failed")),
            path=str(item["path"]) if item.get("path") is not None else None,
        )
        for item in core_result.get("diagnostics", [])
        if isinstance(item, dict)
    )
    return ProjectMetadataValidationResult(
        request=request,
        success=bool(core_result.get("success", False)),
        diagnostics=diagnostics,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )


def validate_contract(request: ContractValidationRequest) -> ContractValidationResult:
    """Validate the repository's current compiled contract bundle."""

    if not isinstance(request, ContractValidationRequest):
        raise InvalidRequestError("request must be a ContractValidationRequest")
    try:
        repository = ArchitectureRepository(request.project_root)
        repository.load()
        internal, sentinel_threshold_exceeded, completeness_threshold_exceeded = (
            _contract_validation_for_repository(
                repository,
                profile=request.profile,
                max_sentinel_fields=request.max_sentinel_fields,
                max_non_complete_entities=request.max_non_complete_entities,
            )
        )
    except Exception as exc:
        raise OperationError("Contract validation could not complete") from exc

    issues = tuple(
        ContractValidationIssue(path=issue.path, message=issue.message) for issue in internal.issues
    )
    diagnostics = tuple(
        Diagnostic(severity="error", code="contract.issue", message=issue.message, path=issue.path)
        for issue in issues
    ) + _threshold_diagnostics(
        internal,
        max_sentinel_fields=request.max_sentinel_fields,
        max_non_complete_entities=request.max_non_complete_entities,
    )
    return ContractValidationResult(
        request=request,
        success=(
            internal.is_valid
            and not sentinel_threshold_exceeded
            and not completeness_threshold_exceeded
        ),
        profile=internal.profile,
        outcome=internal.outcome,
        sentinel_field_count=internal.sentinel_field_count,
        non_complete_entity_count=internal.non_complete_entity_count,
        completeness_counts=MappingProxyType(dict(internal.completeness_counts or {})),
        issues=issues,
        diagnostics=diagnostics,
        package_version=__version__,
        api_contract_version=API_CONTRACT_VERSION,
    )


def validate_generated_docs(
    request: GeneratedDocsValidationRequest,
) -> GeneratedDocsValidationResult:
    """Validate covered generated documentation artifacts for one scope."""

    if not isinstance(request, GeneratedDocsValidationRequest):
        raise InvalidRequestError("request must be a GeneratedDocsValidationRequest")
    try:
        resolver = ProjectScopeResolver(explicit_scope=request.project_root)
        scope = resolver.resolve()
        results = GeneratedArtifactValidator(scope_resolver=resolver).validate_scope(scope)
    except Exception as exc:
        raise OperationError("Generated documentation validation could not complete") from exc

    artifacts = tuple(
        sorted(
            (
                GeneratedArtifactValidation(
                    artifact_path=_display_path(request.project_root, item.artifact_path) or "",
                    status=cast(
                        Literal[
                            "valid",
                            "stale_generated_output",
                            "tampered_generated_output",
                            "missing_or_malformed_integrity_header",
                            "unsupported_artifact_kind",
                        ],
                        item.status,
                    ),
                    artifact_kind=item.artifact_kind,
                    reason_code=item.reason_code,
                    expected_source_hash=item.expected_source_hash,
                    actual_source_hash=item.actual_source_hash,
                    expected_rendered_hash=item.expected_rendered_hash,
                    actual_rendered_hash=item.actual_rendered_hash,
                    notes=tuple(item.notes),
                )
                for item in results
            ),
            key=lambda item: item.artifact_path,
        )
    )
    diagnostics = tuple(
        Diagnostic(
            severity="error",
            code=f"generated_docs.{item.reason_code}",
            message=(item.notes[0] if item.notes else item.reason_code),
            path=item.artifact_path,
        )
        for item in artifacts
        if item.status != GeneratedArtifactStatus.VALID.value
    )
    return GeneratedDocsValidationResult(
        request=request,
        success=all(item.status == GeneratedArtifactStatus.VALID.value for item in artifacts),
        artifacts=artifacts,
        diagnostics=diagnostics,
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
        check=request.check,
        output_dir=output_root if request.write else None,
        pinned_timestamp=request.timestamp,
        include_system_overview=request.include_system_overview,
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
                        artifact_id=_artifact_id(
                            item.path.as_posix(),
                            logical_id=getattr(item, "logical_id", None),
                        ),
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
        if repository.model_version in {"2.0", "2.1", "2.2"}:
            model = (
                repository.get_model_v22()
                if repository.model_version == "2.2"
                else (
                    repository.get_model_v21()
                    if repository.model_version == "2.1"
                    else repository.get_model_v2()
                )
            )
            core_result = execute_repository_validation(
                model_version=repository.model_version,
                architecture_namespace=model.architecture_namespace,
                entities=repository.get_entities(),
            )
            if not core_result.get("success", False):
                message = "; ".join(
                    str(item.get("message", "repository identity validation failed"))
                    for item in core_result.get("diagnostics", [])
                    if isinstance(item, dict)
                )
                raise ArchitectureRegistryError(message or "Repository identity validation failed")
        return repository
    except ArchitectureRegistryError as exc:
        raise RepositoryError("Architecture repository could not be opened") from exc
    except Exception as exc:
        raise RepositoryError("Architecture repository could not be opened") from exc


@implements_adr("ADR-L-0019", "ADR-L-0012")
def open_provider_registry(
    workspace_roots: Mapping[str, str | Path],
) -> ProviderRegistry:
    """Open a read-only provider registry through shared routing semantics."""

    if not isinstance(workspace_roots, Mapping) or not workspace_roots:
        raise InvalidRequestError("workspace_roots must be a non-empty mapping")
    normalized: dict[str, Path] = {}
    for key, value in workspace_roots.items():
        if not isinstance(key, str) or not key:
            raise InvalidRequestError("workspace routing keys must be non-empty strings")
        normalized[key] = _normalize_project_root(value)
    try:
        bindings: list[ProviderBinding] = []
        core_bindings: list[dict[str, str]] = []
        for key in sorted(normalized):
            root = normalized[key]
            payload = yaml.safe_load((root / "PROJECT.yaml").read_text(encoding="utf-8"))
            namespace = (
                payload.get("architecture_documentation", {}).get("architecture_namespace")
                if isinstance(payload, dict)
                else None
            )
            if not isinstance(namespace, str) or not namespace:
                raise ArchitectureRegistryError(
                    "PROJECT.yaml missing architecture_documentation.architecture_namespace: "
                    f"{root / 'PROJECT.yaml'}"
                )
            repository = ArchitectureRepository(project_root=root)
            repository.load()
            bindings.append(
                ProviderBinding(
                    workspace_key=key,
                    architecture_namespace=namespace,
                    project_root=root,
                    repository=repository,
                )
            )
            core_bindings.append(
                {
                    "workspace_key": key,
                    "architecture_namespace": namespace,
                    "project_root": root.as_posix(),
                }
            )
        result = execute_provider_registry(core_bindings)
        if not result.get("success", False):
            messages = "; ".join(
                str(item.get("message", "provider registry validation failed"))
                for item in result.get("diagnostics", [])
                if isinstance(item, dict)
            )
            raise ArchitectureRegistryError(messages or "Provider registry validation failed")
        return ProviderRegistry(tuple(bindings))
    except ArchitectureRegistryError as exc:
        raise RepositoryError("Provider registry could not be opened") from exc
