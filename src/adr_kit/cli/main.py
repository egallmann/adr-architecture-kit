"""CLI for ADR toolkit.

Implements ADR-L-0002: Multi-scope ADR architecture with scope-aware commands.
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional, cast

try:
    import click
except ImportError:
    print("Error: click package not installed. Install with: pip install adr-architecture-kit")
    sys.exit(1)

import yaml

from ..api import LinkageProvenance, _operations as application_service
from ..generators import (
    LogicalADRGenerator,
    PhysicalComponentADRGenerator,
    PhysicalSystemADRGenerator,
    ScaffoldGenerator,
    SystemOverviewGenerator,
)
from ..compiler import (
    AdrIrFragmentCompileError,
    ArchitectureCompiler,
    CompilerConfig,
    compile_logical_adr_ir_fragments,
)
from ..compiler.pipeline import run_frontend_pipeline
from ..decorators import implements_adr
from ..models.implementation_attribution import (
    ImplementationAttributionEvidenceV15,
    ImplementationAttributionEvidenceV16,
)
from adr_kit.semantic_attribution.normalize import (
    evidence_to_canonical_dict,
    normalize_attribution_evidence,
    relationship_occurrence_counts,
    unique_semantic_edges,
)
from ..integrity import GeneratedArtifactStatus
from ..migrators.canonical_id_normalizer import CanonicalIdNormalizer
from ..migrators.identity_v13 import IdentityV13Migrator, IdentityMapDocument
from ..migrators.topology_identity import TopologyIdentityMigrator
from ..parser import ADRParser
from ..repository import ArchitectureRepository
from ..schema.contract_validation import ContractProfile, validate_adr_contract_bundle
from ..schema.implementation_attribution_validation import (
    validate_implementation_attribution_evidence,
)
from ..attribution_shim_generator import generate_shim
from ..federation.workspace_attribution import (
    resolve_workspace_repos,
    write_workspace_attribution_federation,
)
from ..validators import (
    ADRValidator,
    GeneratedArtifactValidator,
    find_import_deprecations,
    format_findings,
    format_outdated_packages,
    list_outdated_packages,
    load_direct_dependency_names,
    run_pip_audit,
    SystemOverviewValidator,
    ValidationResult as ValidatorValidationResult,
)
from ..scope import ProjectScopeResolver
from .. import __version__


def _discover_scope_adr_files(scope) -> list[Path]:
    """Discover ADR source files for rendered markdown generation."""
    files: list[Path] = []
    for directory in (
        scope.logical_dir,
        scope.physical_dir,
        scope.adr_dir / "physical-system",
        scope.adr_dir / "physical-component",
    ):
        if not directory.exists():
            continue
        files.extend(
            sorted(
                path
                for path in directory.glob("*.yaml")
                if path.is_file() and not path.is_symlink()
            )
        )
    return files


def _architecture_index_path(scope) -> Path:
    """Return canonical architecture index output path for a scope."""
    return scope.adr_dir / "index" / "architecture-index.yaml"


def _load_architecture_repository(scope_path: Optional[Path]) -> ArchitectureRepository:
    """Load repository-backed architecture discovery state."""
    repository = ArchitectureRepository(
        scope_resolver=ProjectScopeResolver(explicit_scope=scope_path)
    )
    repository.load()
    return repository


def _dump_yaml(data) -> str:
    """Render CLI output as deterministic YAML."""
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip()


def _dump_entities(entities) -> str:
    """Render normalized entities as deterministic YAML."""
    return _dump_yaml(
        {"entities": [entity.model_dump(mode="json", exclude_none=True) for entity in entities]}
    )


def _dump_relationships(relationships) -> str:
    """Render relationship records as deterministic YAML."""
    return _dump_yaml(
        {
            "relationships": [
                relationship.model_dump(mode="json", exclude_none=True)
                for relationship in relationships
            ]
        }
    )


def _maybe_show_input_schema(generator_cls, show_input_schema: bool) -> bool:
    """Render generator input schema and short-circuit command execution."""
    if not show_input_schema:
        return False
    click.echo(_dump_yaml(generator_cls.input_json_schema()))
    return True


def _require_generation_paths(
    input_path: Optional[Path], output: Optional[Path]
) -> tuple[Path, Path]:
    """Validate required paths for source generation commands."""
    if input_path is None:
        raise ValueError("--input is required unless --show-input-schema is used")
    if output is None:
        raise ValueError("--output is required unless --show-input-schema is used")
    return input_path, output


def _run_cli_subcommand(args: list[str]) -> int:
    """Execute a CLI subcommand in-process."""
    try:
        cli.main(args=args, prog_name="adr", standalone_mode=False)
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1


def _run_governance_checks(scope: Path, *, skip_tests: bool) -> int:
    """Run the standard governance validation bundle."""
    failures = 0
    scope_root = scope.resolve()

    steps: list[tuple[str, list[str]]] = [
        (
            "ADR validation and governance references",
            [
                "validate",
                "--scope",
                str(scope_root),
                "--mode",
                "complete",
                "--cross-references",
            ],
        ),
        (
            "Greenfield contract validation",
            [
                "validate-contract",
                "--scope",
                str(scope_root),
                "--contract-profile",
                "greenfield",
            ],
        ),
        (
            "Brownfield ratchet validation",
            [
                "validate-contract",
                "--scope",
                str(scope_root),
                "--contract-profile",
                "brownfield",
                "--max-sentinel-fields",
                "0",
                "--max-non-complete-entities",
                "0",
            ],
        ),
    ]

    for label, args in steps:
        click.echo(f"\n== {label} ==")
        click.echo("adr " + " ".join(args))
        failures += _run_cli_subcommand(args)

    if not skip_tests:
        test_command = [sys.executable, "-m", "pytest", "tests", "-q"]
        click.echo("\n== Full test suite ==")
        click.echo(" ".join(test_command))
        failures += subprocess.run(test_command, cwd=scope_root).returncode

    return failures


def _ordered_scopes(scope_path: Optional[Path]) -> list:
    """Resolve scopes in deterministic root-first order."""
    resolver = ProjectScopeResolver(explicit_scope=scope_path)
    scopes = resolver.resolve_recursive()
    if not scopes:
        return []
    root_scope = scopes[0]
    sub_scopes = sorted(scopes[1:], key=lambda current: current.root.as_posix())
    return [root_scope, *sub_scopes]


def _run_recursive_governance_checks(scope: Path, *, skip_tests: bool) -> int:
    """Run the standard governance validation bundle across all detected scopes."""
    failures = 0
    scope_root = scope.resolve()

    steps: list[tuple[str, list[str]]] = [
        (
            "ADR validation",
            [
                "validate",
                "--scope",
                str(scope_root),
                "--mode",
                "complete",
                "--recursive",
            ],
        ),
        (
            "Greenfield contract validation",
            [
                "validate-contract",
                "--scope",
                str(scope_root),
                "--contract-profile",
                "greenfield",
                "--recursive",
            ],
        ),
        (
            "Brownfield ratchet validation",
            [
                "validate-contract",
                "--scope",
                str(scope_root),
                "--contract-profile",
                "brownfield",
                "--max-sentinel-fields",
                "0",
                "--max-non-complete-entities",
                "0",
                "--recursive",
            ],
        ),
        (
            "Generated documentation validation",
            [
                "validate-generated-docs",
                "--scope",
                str(scope_root),
                "--recursive",
            ],
        ),
        (
            "Project metadata validation",
            [
                "validate-project-metadata",
                "--scope",
                str(scope_root),
                "--recursive",
            ],
        ),
    ]

    for label, args in steps:
        click.echo(f"\n== {label} ==")
        click.echo("adr " + " ".join(args))
        failures += _run_cli_subcommand(args)

    validator = ADRValidator(scope_resolver=ProjectScopeResolver(explicit_scope=scope_root))
    for current_scope in _ordered_scopes(scope_root):
        click.echo(f"\n== Cross-reference validation ({current_scope.name}) ==")
        result = validator.validate_cross_references(current_scope.adr_dir)
        if result.has_errors:
            for error in result.errors:
                click.echo(f"ERROR: {error.message}")
            failures += 1
        else:
            click.echo("Cross-references valid")

    if not skip_tests:
        test_command = [sys.executable, "-m", "pytest", "tests", "-q"]
        click.echo("\n== Full test suite ==")
        click.echo(" ".join(test_command))
        failures += subprocess.run(test_command, cwd=scope_root).returncode

    return failures


def _parse_emit_list(value: str | None) -> set[str]:
    """Parse `adr compile --emit` values."""
    allowed = {"registries", "manifest", "markdown", "graph"}
    if not value:
        return {"registries", "manifest", "markdown"}
    emit = {item.strip() for item in value.split(",") if item.strip()}
    unknown = sorted(emit - allowed)
    if unknown:
        raise ValueError(f"Unknown emit target(s): {', '.join(unknown)}")
    return emit


def _artifact_by_path(result, relative_path: str):
    """Return an emitted artifact by its relative path."""
    for artifact in result.artifacts:
        if artifact.path.as_posix() == relative_path:
            return artifact
    raise ValueError(f"Expected emitted artifact not found: {relative_path}")


def _load_yaml_artifact(artifact) -> dict:
    """Parse a YAML-emitted compiler artifact."""
    return yaml.safe_load(artifact.content.decode("utf-8"))


def _echo_compilation_result(
    scope,
    result,
    *,
    mode: str,
    check: bool,
    dry_run: bool,
    validate_contract: bool,
    contract_profile: str,
) -> None:
    """Print a single-scope compilation summary."""
    click.echo(f"Project scope: {scope.name} ({scope.root})")
    click.echo(f"Mode: {mode}")
    click.echo(f"Success: {result.success}")
    click.echo(f"Artifacts emitted: {result.statistics.artifacts_emitted}")
    click.echo(f"Entities: {result.statistics.entities_extracted}")
    click.echo(f"Relationships: {result.statistics.relationships_derived}")
    click.echo(f"Unresolved: {result.statistics.unresolved_detected}")
    if check:
        click.echo("Check mode: enabled")
    elif dry_run:
        click.echo("Dry run: enabled")
    if validate_contract:
        click.echo(f"Contract validation: {contract_profile}")
    for artifact in sorted(result.artifacts, key=lambda item: item.path.as_posix()):
        click.echo(f"  {artifact.kind}: {artifact.path.as_posix()}")
    for diagnostic in result.diagnostics.as_list():
        click.echo(f"{diagnostic.level.name}: {diagnostic.code} {diagnostic.message}")


def _echo_recursive_compilation_result(
    result, *, mode: str, check: bool, dry_run: bool, validate_contract: bool, contract_profile: str
) -> None:
    """Print a recursive multi-scope compilation summary."""
    click.echo("Compiling architecture artifacts recursively...")
    click.echo(f"Mode: {mode}")
    click.echo(f"Success: {result.success}")
    click.echo(f"Scopes compiled: {result.statistics.scopes_compiled}")
    click.echo(f"Successful scopes: {result.statistics.successful_scopes}")
    click.echo(f"Failed scopes: {result.statistics.failed_scopes}")
    if check:
        click.echo("Check mode: enabled")
    elif dry_run:
        click.echo("Dry run: enabled")
    if validate_contract:
        click.echo(f"Contract validation: {contract_profile}")
    for scoped in result.scope_results:
        click.echo(f"\nScope: {scoped.scope.name} ({scoped.scope.root})")
        click.echo(f"  Success: {scoped.result.success}")
        click.echo(f"  Artifacts emitted: {scoped.result.statistics.artifacts_emitted}")
        for artifact in sorted(scoped.result.artifacts, key=lambda item: item.path.as_posix()):
            click.echo(f"    {artifact.kind}: {artifact.path.as_posix()}")
        for diagnostic in scoped.result.diagnostics.as_list():
            click.echo(f"  {diagnostic.level.name}: {diagnostic.code} {diagnostic.message}")


@implements_adr("ADR-L-0002", "ADR-L-0013")
@click.group()
@click.version_option(version=__version__)
def cli():
    """ADR Architecture Kit - Multi-scope ADR management."""
    pass


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("compile-ir-fragments")
@click.option(
    "--scope-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Scope root used to derive deterministic artifact_uri and input_ref values.",
)
@click.option(
    "--adr-file",
    "adr_files",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    multiple=True,
    required=True,
    help="Explicit Logical ADR file to compile. Repeat for multiple ADR-L inputs.",
)
@click.option(
    "--namespace",
    required=True,
    type=str,
    help="Opaque Architecture IR namespace string supplied by the ingestion pipeline.",
)
@click.option(
    "--artifact-kind",
    required=True,
    type=str,
    help="Artifact kind recorded in provenance.source.artifact_kind.",
)
@click.option(
    "--last-updated",
    required=True,
    type=str,
    help="Fixed pipeline-supplied timestamp for provenance.last_updated.",
)
@click.option(
    "--adapter-schema-version",
    default="logical_adr_ir_fragment.v1",
    show_default=True,
    type=str,
    help="Logical ADR to Architecture IR adapter profile version.",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output path for the canonical JSON fragment array.",
)
def compile_ir_fragments(
    scope_root: Optional[Path],
    adr_files: tuple[Path, ...],
    namespace: str,
    artifact_kind: str,
    last_updated: str,
    adapter_schema_version: str,
    output: Path,
):
    """Compile explicit Logical ADR files into deterministic Architecture IR fragments."""
    try:
        result = compile_logical_adr_ir_fragments(
            adr_file_paths=list(adr_files),
            namespace=namespace,
            artifact_kind=artifact_kind,
            last_updated=last_updated,
            adapter_schema_version=adapter_schema_version,
            scope_root=scope_root,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(result.canonical_fragment_bytes)
        click.echo(f"Compiled {len(result.records)} IR fragment records: {output}")
        click.echo(f"  Entities: {len(result.entities)}")
        click.echo(f"  Relationships: {len(result.relationships)}")
    except AdrIrFragmentCompileError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("build-ir-fragments")
def build_ir_fragments():
    """Repository self-publication example. Not a generic consumer command.

    Builds the ADR IR fragment publication artifact for the adr-architecture-kit
    repository itself, using hardcoded repo-specific paths (ADR-L-9000, dist/).

    This command is an example of how a repository publishes its own ADR-derived
    IR fragments. It is not intended for use in other repositories or as a
    generic product API. For parameterized IR fragment compilation, use the
    `compile-ir-fragments` command instead.
    """
    try:
        click.echo(
            "NOTE: build-ir-fragments is a repository self-publication example, not a "
            "generic consumer command. Use `adr compile-ir-fragments` for parameterized use.",
            err=True,
        )
        # This command intentionally publishes repository-owned example data.
        # Resolve that authority from the checked-out repository, not from the
        # installed package location used to execute the command.
        repo_root = Path.cwd().resolve()
        adr_source_path = (
            repo_root / "adrs" / "logical" / "ADR-L-9000-kernel-boot-publication-surface.yaml"
        )
        output_path = repo_root / "dist" / "architecture-ir" / "adr-ir-fragments.json"

        result = compile_logical_adr_ir_fragments(
            adr_file_paths=[adr_source_path],
            namespace="repo:ste-workspace:boot",
            artifact_kind="logical-adr",
            last_updated="2026-03-21T00:00:00.000Z",
            scope_root=repo_root,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result.canonical_fragment_bytes)
        click.echo(f"Built {len(result.records)} IR fragment records: {output_path}")
    except AdrIrFragmentCompileError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _generate_source_adr(
    input_path: Path,
    output: Path,
    generator_cls,
    parse_method: str,
    label: str,
    required_prefix: str,
    validation_mode: str,
    preserve_empty_sections: bool,
):
    """Generate, save, parse, and validate a source ADR artifact."""
    parser = ADRParser()
    validator = ADRValidator(parser=parser)
    generator = generator_cls(parser=parser, validator=validator)

    adr = generator.create_adr_from_file(input_path, mode=validation_mode)
    adr_id = adr.id if hasattr(adr, "id") else adr["id"]
    adr_title = adr.title if hasattr(adr, "title") else adr["title"]
    if not adr_id.startswith(required_prefix):
        raise ValueError(f"{label} must use ID prefix {required_prefix}, got {adr_id}")

    generator.save_adr(
        adr,
        output,
        mode=validation_mode,
        preserve_empty_sections=preserve_empty_sections,
    )

    if validation_mode == "complete":
        getattr(parser, parse_method)(output)
    result = validator.validate_file(output, mode=validation_mode)

    if result.has_errors:
        click.echo(f"Generated file failed validation: {output}", err=True)
        for error in result.errors:
            click.echo(f"  ERROR: {error.message}", err=True)
        sys.exit(1)

    click.echo(f"Generated {label}: {output}")
    click.echo(f"  ID: {adr_id}")
    click.echo(f"  Title: {adr_title}")

    if result.has_warnings:
        for warning in result.warnings:
            click.echo(f"  WARNING: {warning.message}")


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("generate-logical")
@click.option(
    "--input",
    "input_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured YAML input for the Logical ADR.",
)
@click.option(
    "--output",
    required=False,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to write the generated Logical ADR YAML.",
)
@click.option(
    "--validation-mode",
    type=click.Choice(["complete", "structural"]),
    default="complete",
    show_default=True,
    help="Validation mode for generation.",
)
@click.option(
    "--preserve-empty-sections",
    is_flag=True,
    help="Preserve explicit empty arrays/objects in generated YAML.",
)
@click.option(
    "--show-input-schema",
    is_flag=True,
    help="Print the JSON Schema for the structured input contract and exit.",
)
def generate_logical(
    input_path: Optional[Path],
    output: Optional[Path],
    validation_mode: str,
    preserve_empty_sections: bool,
    show_input_schema: bool,
):
    """Generate a Logical ADR YAML file from structured input."""
    try:
        if _maybe_show_input_schema(LogicalADRGenerator, show_input_schema):
            return
        input_path, output = _require_generation_paths(input_path, output)
        _generate_source_adr(
            input_path,
            output,
            LogicalADRGenerator,
            "parse_logical_adr",
            "Logical ADR",
            "ADR-L-",
            validation_mode,
            preserve_empty_sections,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("generate-vision")
@click.option(
    "--input",
    "input_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured YAML input for the Vision ADR.",
)
@click.option(
    "--output",
    required=False,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to write the generated Vision ADR YAML.",
)
@click.option(
    "--validation-mode",
    type=click.Choice(["complete", "structural"]),
    default="complete",
    show_default=True,
    help="Validation mode for generation.",
)
@click.option(
    "--preserve-empty-sections",
    is_flag=True,
    help="Preserve explicit empty arrays/objects in generated YAML.",
)
@click.option(
    "--show-input-schema",
    is_flag=True,
    help="Print the JSON Schema for the structured input contract and exit.",
)
def generate_vision(
    input_path: Optional[Path],
    output: Optional[Path],
    validation_mode: str,
    preserve_empty_sections: bool,
    show_input_schema: bool,
):
    """Generate a Vision ADR YAML file from structured input."""
    try:
        if _maybe_show_input_schema(LogicalADRGenerator, show_input_schema):
            return
        input_path, output = _require_generation_paths(input_path, output)
        _generate_source_adr(
            input_path,
            output,
            LogicalADRGenerator,
            "parse_logical_adr",
            "Vision ADR",
            "ADR-V-",
            validation_mode,
            preserve_empty_sections,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("generate-manifest")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--recursive", is_flag=True, help="Generate manifests for all sub-modules recursively"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    help="Output path for manifest (default: <scope>/adrs/manifest.yaml)",
)
def generate_manifest(scope: Optional[Path], recursive: bool, output: Optional[Path]):
    """Generate manifest.yaml from ADRs (ADR-L-0002: CAP-0002).

    Auto-detects project scope by default. Use --scope to override.
    Use --recursive to generate manifests for all sub-modules.
    """
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        compiler = ArchitectureCompiler(scope_resolver=resolver)

        if recursive:
            click.echo("Generating manifests recursively...")
            if output is not None:
                raise ValueError(
                    "--output is not supported with --recursive; manifests are emitted per scope"
                )
            workspace_result = compiler.compile_recursive(
                config=CompilerConfig(emit={"manifest"}),
            )
            if not workspace_result.success:
                raise ValueError("Architecture compilation failed")
            for scoped in workspace_result.scope_results:
                click.echo(
                    f"Generated manifest for {scoped.scope.name}: {scoped.scope.manifest_path}"
                )
            click.echo(f"\nGenerated {workspace_result.statistics.scopes_compiled} manifests")
        else:
            click.echo("Generating manifest...")
            detected_scope = resolver.resolve()
            click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")

            if output is None:
                result = compiler.compile(
                    detected_scope,
                    CompilerConfig(emit={"manifest"}),
                )
                if not result.success:
                    raise ValueError("Architecture compilation failed")
                output_path = detected_scope.manifest_path
            else:
                result = compiler.compile(
                    detected_scope,
                    CompilerConfig(emit={"manifest"}, dry_run=True),
                )
                if not result.success:
                    raise ValueError("Architecture compilation failed")
                output_path = output
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(_artifact_by_path(result, "adrs/manifest.yaml").content)
            manifest = _load_yaml_artifact(_artifact_by_path(result, "adrs/manifest.yaml"))
            statistics = manifest["statistics"]
            click.echo(f"Generated manifest: {output_path}")
            click.echo(f"  ADRs: {statistics['total_adrs']}")
            click.echo(f"  Logical: {statistics['logical_adrs']}")
            click.echo(f"  Physical: {statistics['physical_adrs']}")
            if statistics["physical_system_adrs"] > 0:
                click.echo(f"  Physical-System: {statistics['physical_system_adrs']}")
            if statistics["physical_component_adrs"] > 0:
                click.echo(f"  Physical-Component: {statistics['physical_component_adrs']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("next-id")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--type",
    "adr_type",
    required=True,
    type=click.Choice(["logical", "physical-system", "physical-component"]),
    help="ADR type to allocate a next ID for.",
)
def next_id(scope: Optional[Path], adr_type: str):
    """Print the next available ADR ID for forward-authoring ADR types."""
    try:
        repository = ArchitectureRepository(
            scope_resolver=ProjectScopeResolver(explicit_scope=scope)
        )
        click.echo(repository.next_id(adr_type))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("scaffold")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope used to derive the next ADR ID when --id is omitted",
)
@click.option(
    "--type",
    "adr_type",
    required=True,
    type=click.Choice(["logical", "physical-system", "physical-component"]),
    help="ADR type scaffold to emit.",
)
@click.option("--id", "adr_id", help="Explicit ADR ID for the scaffold.")
@click.option("--title", help="Override scaffold title.")
@click.option("--include-optional", is_flag=True, help="Include optional scaffold sections.")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Optional file path to write the scaffold YAML.",
)
def scaffold(
    scope: Optional[Path],
    adr_type: str,
    adr_id: Optional[str],
    title: Optional[str],
    include_optional: bool,
    output: Optional[Path],
):
    """Generate a structured ADR input scaffold."""
    try:
        resolved_id = adr_id
        if resolved_id is None:
            repository = ArchitectureRepository(
                scope_resolver=ProjectScopeResolver(explicit_scope=scope)
            )
            resolved_id = repository.next_id(adr_type)
        generator = ScaffoldGenerator()
        rendered = generator.scaffold_yaml(
            adr_type,
            adr_id=resolved_id,
            title=title,
            include_optional=include_optional,
        )
        if output is None:
            click.echo(rendered.rstrip())
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
            click.echo(f"Generated scaffold: {output}")
            click.echo(f"  ID: {resolved_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("generate-physical-component")
@click.option(
    "--input",
    "input_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured YAML input for the Physical-Component ADR.",
)
@click.option(
    "--output",
    required=False,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to write the generated Physical-Component ADR YAML.",
)
@click.option(
    "--validation-mode",
    type=click.Choice(["complete", "structural"]),
    default="complete",
    show_default=True,
    help="Validation mode for generation.",
)
@click.option(
    "--preserve-empty-sections",
    is_flag=True,
    help="Preserve explicit empty arrays/objects in generated YAML.",
)
@click.option(
    "--show-input-schema",
    is_flag=True,
    help="Print the JSON Schema for the structured input contract and exit.",
)
def generate_physical_component(
    input_path: Optional[Path],
    output: Optional[Path],
    validation_mode: str,
    preserve_empty_sections: bool,
    show_input_schema: bool,
):
    """Generate a Physical-Component ADR YAML file from structured input."""
    try:
        if _maybe_show_input_schema(PhysicalComponentADRGenerator, show_input_schema):
            return
        input_path, output = _require_generation_paths(input_path, output)
        _generate_source_adr(
            input_path,
            output,
            PhysicalComponentADRGenerator,
            "parse_physical_component_adr",
            "Physical-Component ADR",
            "ADR-PC-",
            validation_mode,
            preserve_empty_sections,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("generate-physical-system")
@click.option(
    "--input",
    "input_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured YAML input for the Physical-System ADR.",
)
@click.option(
    "--output",
    required=False,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to write the generated Physical-System ADR YAML.",
)
@click.option(
    "--validation-mode",
    type=click.Choice(["complete", "structural"]),
    default="complete",
    show_default=True,
    help="Validation mode for generation.",
)
@click.option(
    "--preserve-empty-sections",
    is_flag=True,
    help="Preserve explicit empty arrays/objects in generated YAML.",
)
@click.option(
    "--show-input-schema",
    is_flag=True,
    help="Print the JSON Schema for the structured input contract and exit.",
)
def generate_physical_system(
    input_path: Optional[Path],
    output: Optional[Path],
    validation_mode: str,
    preserve_empty_sections: bool,
    show_input_schema: bool,
):
    """Generate a Physical-System ADR YAML file from structured input."""
    try:
        if _maybe_show_input_schema(PhysicalSystemADRGenerator, show_input_schema):
            return
        input_path, output = _require_generation_paths(input_path, output)
        _generate_source_adr(
            input_path,
            output,
            PhysicalSystemADRGenerator,
            "parse_physical_system_adr",
            "Physical-System ADR",
            "ADR-PS-",
            validation_mode,
            preserve_empty_sections,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("generate-entity-registry")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--recursive", is_flag=True, help="Generate entity registries for all sub-modules recursively"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    help="Output path for registry (default: <scope>/adrs/entities/registry.yaml)",
)
def generate_entity_registry(scope: Optional[Path], recursive: bool, output: Optional[Path]):
    """Generate the legacy entity-registry.yaml compatibility artifact."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        compiler = ArchitectureCompiler(scope_resolver=resolver)

        if recursive:
            click.echo(
                "Generating architecture indexes recursively for legacy entity registry compatibility..."
            )
            if output is None:
                workspace_result = compiler.compile_recursive(
                    config=CompilerConfig(emit={"registries"}),
                )
                if not workspace_result.success:
                    raise ValueError("Architecture compilation failed")
                for scoped in workspace_result.scope_results:
                    click.echo(
                        f"Generated legacy entity registry for {scoped.scope.name}: {scoped.scope.adr_dir / 'entities' / 'registry.yaml'}"
                    )
                    click.echo(
                        f"  Architecture index: {scoped.scope.adr_dir / 'index' / 'architecture-index.yaml'}"
                    )

                click.echo(
                    f"\nGenerated legacy entity registry compatibility artifacts for {workspace_result.statistics.scopes_compiled} scope(s)"
                )
            else:
                scopes = resolver.resolve_recursive()
                for scope_obj in scopes:
                    if not scope_obj.adr_dir.exists():
                        continue
                    scope_name = scope_obj.name or str(scope_obj.root)
                    result = compiler.compile(
                        scope_obj,
                        CompilerConfig(emit={"registries"}, dry_run=True),
                    )
                    if not result.success:
                        raise ValueError("Architecture compilation failed")
                    output_path = output
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(
                        _artifact_by_path(result, "adrs/entities/registry.yaml").content
                    )
                    click.echo(f"Generated legacy entity registry for {scope_name}: {output_path}")
                    click.echo(
                        f"  Architecture index: {scope_obj.adr_dir / 'index' / 'architecture-index.yaml'}"
                    )

                click.echo(
                    f"\nGenerated legacy entity registry compatibility artifacts for {len(scopes)} scope(s)"
                )
        else:
            click.echo(
                "Generating architecture index and legacy entity registry compatibility artifact..."
            )
            detected_scope = resolver.resolve()
            click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")
            if output is None:
                result = compiler.compile(
                    detected_scope,
                    CompilerConfig(emit={"registries"}),
                )
                if not result.success:
                    raise ValueError("Architecture compilation failed")
                output_path = detected_scope.adr_dir / "entities" / "registry.yaml"
            else:
                result = compiler.compile(
                    detected_scope,
                    CompilerConfig(emit={"registries"}, dry_run=True),
                )
                if not result.success:
                    raise ValueError("Architecture compilation failed")
                output_path = output
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(
                    _artifact_by_path(result, "adrs/entities/registry.yaml").content
                )

            click.echo(f"Generated legacy entity registry: {output_path}")
            click.echo(f"  Architecture index: {_architecture_index_path(detected_scope)}")
            legacy_payload = yaml.safe_load(
                _artifact_by_path(result, "adrs/entities/registry.yaml").content
            )
            click.echo(f"  Entities: {len(legacy_payload.get('entities', []))}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("generate-architecture-index")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
def generate_architecture_index(scope: Optional[Path]):
    """Generate normalized architecture discovery artifacts under adrs/index/."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        compiler = ArchitectureCompiler(scope_resolver=resolver)
        detected_scope = resolver.resolve()
        click.echo("Generating architecture discovery index...")
        click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")
        result = compiler.compile(
            detected_scope,
            CompilerConfig(emit={"registries"}),
        )
        if not result.success:
            raise ValueError("Architecture compilation failed")
        click.echo(f"Generated architecture index: {_architecture_index_path(detected_scope)}")
        click.echo(f"  Entities: {result.statistics.entities_extracted}")
        click.echo(f"  Relationships: {result.statistics.relationships_derived}")
        click.echo(f"  Unresolved: {result.statistics.unresolved_detected}")
        click.echo(
            f"  Legacy entity registry: {detected_scope.adr_dir / 'entities' / 'registry.yaml'}"
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("compile")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--emit",
    default="registries,manifest,markdown",
    show_default=True,
    help="Comma-separated emit targets: registries, manifest, markdown.",
)
@click.option(
    "--timestamp",
    type=str,
    default=None,
    help="Pinned timestamp for deterministic compilation (ISO-8601).",
)
@click.option(
    "--mode",
    type=click.Choice(["normal", "strict", "lenient"]),
    default="normal",
    show_default=True,
    help="Compilation success policy.",
)
@click.option("--dry-run", is_flag=True, help="Compile without writing files.")
@click.option(
    "--check", is_flag=True, help="Compile in-memory and fail if selected on-disk artifacts drift."
)
@click.option(
    "--validate-contract",
    is_flag=True,
    help="Validate the compiled repository contract bundle from in-memory outputs.",
)
@click.option(
    "--contract-profile",
    type=click.Choice(["greenfield", "brownfield", "migration"]),
    default="greenfield",
    show_default=True,
    help="Contract validation profile used with --validate-contract.",
)
@click.option("--recursive", is_flag=True, help="Compile all detected scopes recursively.")
def compile_artifacts(
    scope: Optional[Path],
    emit: str,
    timestamp: Optional[str],
    mode: str,
    dry_run: bool,
    check: bool,
    validate_contract: bool,
    contract_profile: str,
    recursive: bool,
):
    """Compile selected architecture artifacts through the unified compiler driver."""
    try:
        click.echo(
            "WARNING: adr compile is deprecated for runtime machine artifacts. "
            "Use `ste architecture compile --project-root <repo>` (ste-runtime) for runtime-owned machine artifacts. "
            "This Python path remains for migration / golden parity only. "
            "See ste-runtime COMPILER-AUTHORITY.md and adr-architecture-kit AUTHORING-SYSTEM.md.",
            err=True,
        )
        emit_targets = _parse_emit_list(emit)
        detected_scope, result = application_service.compile_for_cli(
            scope,
            emit_targets=emit_targets,
            timestamp=timestamp,
            mode=mode,
            dry_run=dry_run,
            check=check,
            validate_contract=validate_contract,
            contract_profile=contract_profile,
            recursive=recursive,
        )
        if recursive:
            _echo_recursive_compilation_result(
                result,
                mode=mode,
                check=check,
                dry_run=dry_run,
                validate_contract=validate_contract,
                contract_profile=contract_profile,
            )
        else:
            if detected_scope is None:
                raise RuntimeError("Compilation scope was not resolved")
            click.echo("Compiling architecture artifacts...")
            _echo_compilation_result(
                detected_scope,
                result,
                mode=mode,
                check=check,
                dry_run=dry_run,
                validate_contract=validate_contract,
                contract_profile=contract_profile,
            )

        if not result.success:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("repair-canonical-ids")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--apply",
    "apply_repairs",
    is_flag=True,
    help="Apply the planned canonical repair through ADR Kit-owned writes.",
)
@click.option(
    "--check",
    is_flag=True,
    help="Fail when a repair is required; intended for CI validation.",
)
@click.option(
    "--resolution-map",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Occurrence-scoped YAML mapping for ambiguous keepers or references.",
)
def repair_canonical_ids(
    scope: Optional[Path],
    apply_repairs: bool,
    check: bool,
    resolution_map: Optional[Path],
) -> None:
    """Plan, apply, or check monotonic canonical entity-ID repairs."""
    try:
        if apply_repairs and check:
            raise ValueError("--apply and --check are mutually exclusive")
        resolver = ProjectScopeResolver(explicit_scope=scope)
        normalizer = CanonicalIdNormalizer(scope_resolver=resolver)
        detected_scope = resolver.resolve()
        plan = normalizer.plan(detected_scope, resolution_map=resolution_map)
        for remap in plan.remaps:
            relative = remap.file_path.resolve().relative_to(detected_scope.root.resolve())
            click.echo(
                f"{relative.as_posix()}#{remap.source_pointer}: "
                f"{remap.old_id} -> {remap.new_id}"
            )
        for ambiguity in plan.ambiguities:
            relative = ambiguity.file_path.resolve().relative_to(detected_scope.root.resolve())
            click.echo(
                f"Ambiguous reference: {relative.as_posix()}#"
                f"{ambiguity.source_pointer} ({ambiguity.entity_id})",
                err=True,
            )
        if check:
            findings = normalizer.validate_allocations(detected_scope)
            if plan.remaps or plan.ambiguities or findings:
                for finding in findings:
                    click.echo(f"Allocation error: {finding}", err=True)
                click.echo("Canonical ID repair required.", err=True)
                raise click.exceptions.Exit(1)
            click.echo("Canonical ID allocation and collision check passed.")
            return
        if not plan.remaps and not apply_repairs:
            click.echo("No canonical ID collisions found. No changes made.")
            return
        if not apply_repairs:
            click.echo(f"Planned {len(plan.remaps)} canonical ID repairs; no files changed.")
            if plan.ambiguities:
                click.echo("Resolve ambiguous references before applying this plan.", err=True)
            return
        applied = normalizer.repair(detected_scope, apply=True, resolution_map=resolution_map)
        click.echo(f"Applied {len(applied.remaps)} canonical ID repairs.")
        if not applied.remaps:
            click.echo("Synchronized the canonical ID allocation ledger.")
        click.echo(
            f"Allocation ledger: "
            f"{detected_scope.adr_dir / 'migrations' / 'canonical-id-allocation.yaml'}"
        )
        click.echo(
            f"Migration ledger: "
            f"{detected_scope.adr_dir / 'migrations' / 'canonical-id-remap.yaml'}"
        )
        click.echo("Run `adr validate --scope . --mode complete` and regenerate projections.")
    except click.exceptions.Exit:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise click.exceptions.Exit(1) from exc


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("normalize-canonical-ids")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
def normalize_canonical_ids(scope: Optional[Path]):
    """Normalize canonical entity ID collisions across ADR YAML files."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        normalizer = CanonicalIdNormalizer(scope_resolver=resolver)
        detected_scope = resolver.resolve()
        click.echo("Normalizing canonical entity ID collisions...")
        click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")
        remaps = normalizer.normalize(detected_scope)
        if not remaps:
            click.echo("No canonical ID collisions found. No changes made.")
            click.echo("Run `adr generate-architecture-index --scope .`")
            return
        click.echo(f"Normalized {len(remaps)} canonical ID collisions.")
        click.echo(
            f"Migration ledger: {detected_scope.adr_dir / 'migrations' / 'canonical-id-remap.yaml'}"
        )
        click.echo("Run `adr generate-architecture-index --scope .`")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0018")
@cli.command("migrate-topology-ids")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--apply",
    "apply_migration",
    is_flag=True,
    help="Apply the planned topology migration through ADR Kit-owned writes.",
)
def migrate_topology_ids(scope: Optional[Path], apply_migration: bool) -> None:
    """Plan or apply stable physical-topology identity migration."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        detected_scope = resolver.resolve()
        migrator = TopologyIdentityMigrator()
        plan = migrator.plan(detected_scope)
        for change in plan.changes:
            relative = change.file_path.resolve().relative_to(detected_scope.root.resolve())
            click.echo(
                f"{relative.as_posix()}#{change.pointer}: " f"{change.before!r} -> {change.after!r}"
            )
        if plan.diagnostics:
            for diagnostic in plan.diagnostics:
                relative = diagnostic.file_path.resolve().relative_to(detected_scope.root.resolve())
                click.echo(
                    f"{diagnostic.code}: {relative.as_posix()}#"
                    f"{diagnostic.pointer}: {diagnostic.message}",
                    err=True,
                )
            raise click.exceptions.Exit(1)
        if not apply_migration:
            click.echo(
                f"Planned {len(plan.changes)} topology changes across "
                f"{len(plan.changed_files)} files; no files changed."
            )
            return
        applied = migrator.apply(detected_scope)
        suffix = "" if len(applied.changed_files) == 1 else "s"
        click.echo(f"Applied topology migration to {len(applied.changed_files)} file{suffix}.")
    except click.exceptions.Exit:
        raise
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise click.exceptions.Exit(1) from exc


@implements_adr("ADR-L-0019")
@cli.command("migrate-identity-v13")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--plan-out",
    type=click.Path(path_type=Path),
    help="Write a complete candidate identity map (mint once after green preflight).",
)
@click.option(
    "--identity-map",
    "identity_map_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Sealed identity map consumed by --apply/--check.",
)
@click.option(
    "--apply",
    "apply_migration",
    is_flag=True,
    help="Atomically apply a sealed identity map (never remints).",
)
@click.option(
    "--check",
    "check_migration",
    is_flag=True,
    help="Verify sealed-map consistency/idempotency without reminting.",
)
@click.option(
    "--recover",
    "recover_journal",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Recover an interrupted identity-migration journal.",
)
def migrate_identity_v13(
    scope: Optional[Path],
    plan_out: Optional[Path],
    identity_map_path: Optional[Path],
    apply_migration: bool,
    check_migration: bool,
    recover_journal: Optional[Path],
) -> None:
    """Plan, seal-consume, check, or recover v1.3 identity migration."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        detected_scope = resolver.resolve()
        migrator = IdentityV13Migrator()
        if recover_journal is not None:
            migrator.recover(recover_journal, detected_scope)
            click.echo(f"Recovered interrupted journal: {recover_journal}")
            return
        if plan_out is not None:
            result = migrator.plan(detected_scope)
            if not result.ok:
                for diagnostic in result.diagnostics:
                    click.echo(f"{diagnostic.code}: {diagnostic.message}", err=True)
                raise click.exceptions.Exit(1)
            plan_out.parent.mkdir(parents=True, exist_ok=True)
            plan_out.write_text(
                yaml.safe_dump(result.identity_map.to_dict(), sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            click.echo(
                f"Wrote candidate identity map ({len(result.identity_map.entries)} entries) "
                f"to {plan_out}"
            )
            return
        if identity_map_path is None:
            raise click.UsageError(
                "Provide --plan-out, or --identity-map with --apply/--check, or --recover"
            )
        payload = yaml.safe_load(identity_map_path.read_text(encoding="utf-8"))
        identity_map = IdentityMapDocument.from_dict(payload)
        if apply_migration:
            writes = migrator.apply(detected_scope, identity_map)
            click.echo(f"Applied sealed identity map across {len(writes)} write(s)")
            return
        if check_migration:
            errors = migrator.check(detected_scope, identity_map)
            if errors:
                for error in errors:
                    click.echo(error, err=True)
                raise click.exceptions.Exit(1)
            click.echo("Identity migration check passed")
            return
        raise click.UsageError("--identity-map requires --apply or --check")
    except click.exceptions.Exit:
        raise
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("validate")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option("--recursive", is_flag=True, help="Validate all sub-modules recursively")
@click.option("--cross-references", is_flag=True, help="Validate cross-references between ADRs")
@click.option(
    "--mode",
    type=click.Choice(["complete", "structural"]),
    default="complete",
    show_default=True,
    help="Validation mode to apply.",
)
def validate(scope: Optional[Path], recursive: bool, cross_references: bool, mode: str):
    """Validate ADRs against schema and business rules (ADR-L-0002: CAP-0003).

    Auto-detects project scope by default. Use --scope to override.
    Use --recursive to validate all sub-modules (ADR-L-0002: INV-0019).
    """
    try:
        detected_scope, results, xref_result = application_service.validate_for_cli(
            scope,
            recursive=recursive,
            cross_references=cross_references,
            mode=mode,
        )

        if recursive:
            click.echo("Validating ADRs recursively...")
            all_results = cast(dict[str, dict[str, ValidatorValidationResult]], results)

            total_files = 0
            total_errors = 0
            total_warnings = 0

            for scope_name, scope_results in all_results.items():
                click.echo(f"\n{scope_name}:")

                errors = sum(1 for result in scope_results.values() if result.has_errors)
                warnings = sum(1 for result in scope_results.values() if result.has_warnings)

                if errors > 0:
                    click.secho(f"  ERROR {errors} files with errors", fg="red")
                if warnings > 0:
                    click.secho(f"  WARN {warnings} files with warnings", fg="yellow")
                if errors == 0 and warnings == 0:
                    click.secho(f"  All {len(scope_results)} files valid", fg="green")

                total_files += len(scope_results)
                total_errors += errors
                total_warnings += warnings

            click.echo(
                f"\nTotal: {total_files} files, {total_errors} errors, {total_warnings} warnings"
            )

            if total_errors > 0:
                sys.exit(1)

        else:
            click.echo("Validating ADRs...")
            if detected_scope is None:
                raise RuntimeError("Validation scope was not resolved")
            click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")
            file_results = cast(dict[str, ValidatorValidationResult], results)

            # Print results
            errors = 0
            warnings = 0

            for file_path, result in file_results.items():
                if result.has_errors:
                    click.secho(f"\nERROR {file_path}", fg="red")
                    for error in result.errors:
                        click.echo(f"  ERROR: {error.message}")
                    errors += 1
                elif result.has_warnings:
                    click.secho(f"\nWARN {file_path}", fg="yellow")
                    for warning in result.warnings:
                        click.echo(f"  WARNING: {warning.message}")
                    warnings += 1

            if errors == 0 and warnings == 0:
                click.secho(f"All {len(file_results)} files valid", fg="green")
            else:
                click.echo(f"\n{len(file_results)} files: {errors} errors, {warnings} warnings")

            # Validate cross-references if requested
            if cross_references:
                click.echo("\nValidating cross-references...")
                if xref_result is None:
                    raise RuntimeError("Cross-reference validation result unavailable")

                if xref_result.has_errors:
                    click.secho("ERROR Cross-reference validation failed", fg="red")
                    for error in xref_result.errors:
                        click.echo(f"  ERROR: {error.message}")
                    sys.exit(1)
                else:
                    click.secho("Cross-references valid", fg="green")

            if errors > 0:
                sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("validate-contract")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--contract-profile",
    type=click.Choice(["greenfield", "brownfield", "migration"]),
    default="greenfield",
    show_default=True,
    help="Contract validation profile to apply.",
)
@click.option(
    "--max-sentinel-fields",
    type=int,
    default=None,
    help="Optional CI threshold. Fail if sentinel-backed field count exceeds this value.",
)
@click.option(
    "--max-non-complete-entities",
    type=int,
    default=None,
    help="Optional CI threshold. Fail if non-complete entity count exceeds this value.",
)
@click.option(
    "--recursive",
    is_flag=True,
    help="Validate the compiled contract bundle for all detected scopes recursively",
)
def validate_contract(
    scope: Optional[Path],
    contract_profile: str,
    max_sentinel_fields: Optional[int],
    max_non_complete_entities: Optional[int],
    recursive: bool,
):
    """Validate the compiled repository contract bundle for the selected profile."""
    try:
        failures = 0
        scopes = (
            _ordered_scopes(scope)
            if recursive
            else [ProjectScopeResolver(explicit_scope=scope).resolve()]
        )
        for index, current_scope in enumerate(scopes):
            if index:
                click.echo()
            repository = _load_architecture_repository(current_scope.root)
            contract_bundle = repository.get_contract_bundle_view()
            click.echo(f"Project scope: {current_scope.name} ({current_scope.root})")

            result = validate_adr_contract_bundle(
                contract_bundle.architecture_index,
                contract_bundle.entity_registry,
                contract_bundle.relationship_registry,
                contract_bundle.unresolved_registry,
                profile=contract_profile,
                remediation_ledger=contract_bundle.remediation_ledger,
            )
            remediation_state_counts = None
            if contract_bundle.remediation_ledger is not None:
                remediation_state_counts = {
                    state: sum(
                        1
                        for entry in contract_bundle.remediation_ledger.entries
                        if entry.state == state
                    )
                    for state in ("sentinel", "pending_approval", "approved")
                }
            sentinel_threshold_exceeded = (
                max_sentinel_fields is not None
                and result.sentinel_field_count > max_sentinel_fields
            )
            completeness_threshold_exceeded = (
                max_non_complete_entities is not None
                and result.non_complete_entity_count > max_non_complete_entities
            )

            click.echo(
                _dump_yaml(
                    {
                        "profile": result.profile,
                        "outcome": result.outcome,
                        "sentinel_field_count": result.sentinel_field_count,
                        "max_sentinel_fields": max_sentinel_fields,
                        "sentinel_threshold_exceeded": sentinel_threshold_exceeded,
                        "non_complete_entity_count": result.non_complete_entity_count,
                        "max_non_complete_entities": max_non_complete_entities,
                        "completeness_threshold_exceeded": completeness_threshold_exceeded,
                        "completeness_counts": result.completeness_counts,
                        "remediation_ledger_present": contract_bundle.remediation_ledger
                        is not None,
                        "remediation_state_counts": remediation_state_counts,
                        "issues": [
                            {"path": issue.path, "message": issue.message}
                            for issue in result.issues
                        ],
                    }
                )
            )

            if (
                not result.is_valid
                or sentinel_threshold_exceeded
                or completeness_threshold_exceeded
            ):
                failures += 1

        if failures:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("governance-checks")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Project scope root to validate.",
)
@click.option("--skip-tests", is_flag=True, help="Skip the full pytest run.")
@click.option(
    "--recursive", is_flag=True, help="Run governance checks for all detected scopes recursively."
)
def governance_checks(scope: Path, skip_tests: bool, recursive: bool):
    """Run the standard local governance validation bundle."""
    try:
        failures = (
            _run_recursive_governance_checks(scope, skip_tests=skip_tests)
            if recursive
            else _run_governance_checks(scope, skip_tests=skip_tests)
        )
        if failures:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.group("entities")
def entities_cli():
    """Query the generated architecture discovery bundle."""
    pass


@implements_adr("ADR-L-0002", "ADR-L-0013")
@entities_cli.command("list")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--type",
    "entity_type",
    type=click.Choice(
        [
            "adr",
            "system",
            "capability",
            "decision",
            "component",
            "invariant",
            "boundary",
            "contract",
            "constraint",
            "nfr",
            "gap",
            "interface",
            "integration",
            "implementation_decision",
        ]
    ),
    help="Filter by entity type",
)
@click.option("--adr", "adr_id", help="Filter by ADR reference")
@click.option("--domain", help="Filter by domain")
@click.option(
    "--status",
    type=click.Choice(["proposed", "active", "deprecated", "superseded"]),
    help="Filter by lifecycle stage",
)
def entities_list(
    scope: Optional[Path],
    entity_type: Optional[str],
    adr_id: Optional[str],
    domain: Optional[str],
    status: Optional[str],
):
    """List entities from the generated registry."""
    try:
        repository = _load_architecture_repository(scope)
        entities = repository.query_entities(
            entity_type=entity_type,
            adr=adr_id,
            domain=domain,
            status=status,
        )
        click.echo(_dump_entities(entities))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0019")
@entities_cli.command("get")
@click.argument("entity_id")
@click.option(
    "--by",
    "lookup_by",
    type=click.Choice(["uuid", "alias-id", "alias-ref", "uri", "auto"]),
    default="auto",
    show_default=True,
    help="Lookup mode (auto is the deprecated unique-alias compatibility path)",
)
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
def entities_get(entity_id: str, lookup_by: str, scope: Optional[Path]) -> None:
    """Get an entity by UUID, alias, URI, or auto compatibility lookup."""
    try:
        repository = _load_architecture_repository(scope)
        if lookup_by == "auto":
            entity = repository.find_entity(entity_id)
        elif lookup_by == "uuid":
            entity = repository.find_entity_by_uuid(entity_id)
        elif lookup_by == "alias-id":
            entity = repository.find_entity_by_alias_id(entity_id)
        elif lookup_by == "alias-ref":
            entity = repository.find_entity_by_alias_ref(entity_id)
        elif lookup_by == "uri":
            entity = repository.resolve_uri(entity_id)
        else:
            raise ValueError(f"Unsupported lookup mode: {lookup_by}")
        if entity is None:
            raise ValueError(f"Entity not found: {entity_id}")
        click.echo(_dump_yaml(entity.model_dump(mode="json", exclude_none=True)))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0019")
@entities_cli.command("aliases")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
def entities_aliases(scope: Optional[Path]) -> None:
    """List deterministic alias inventory for model 2.0 entities."""
    try:
        repository = _load_architecture_repository(scope)
        aliases = repository.list_aliases()
        payload = {
            "aliases": [
                {
                    "uuid": item.uuid,
                    "alias_id": item.alias_id,
                    "alias_name": item.alias_name,
                    "alias_ref": item.alias_ref,
                    "entity_type": item.entity_type,
                    "uri": item.uri,
                }
                for item in aliases
            ]
        }
        click.echo(_dump_yaml(payload))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@entities_cli.command("relationships")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option("--entity", "entity_id", help="Filter relationships to one entity ID")
@click.option(
    "--type",
    "relationship_type",
    type=click.Choice(
        [
            "declared_in",
            "references",
            "related_to",
            "enforces",
            "enabled_by",
            "enables",
            "governs",
            "implemented_by",
            "embodied_in",
            "implements_logical",
            "supersedes",
            "superseded_by",
            "refines",
        ]
    ),
    help="Filter by relationship type",
)
@click.option(
    "--direction",
    type=click.Choice(["any", "incoming", "outgoing"]),
    default="any",
    show_default=True,
    help="Relationship direction when --entity is provided",
)
def entities_relationships(
    scope: Optional[Path],
    entity_id: Optional[str],
    relationship_type: Optional[str],
    direction: str,
):
    """List repository relationship records."""
    try:
        repository = _load_architecture_repository(scope)
        relationships = (
            repository.get_relationships_for_entity(
                entity_id,
                relationship_type=relationship_type,
                direction=direction,
            )
            if entity_id
            else [
                relationship
                for relationship in repository.get_relationships()
                if relationship_type is None or relationship.relationship_type == relationship_type
            ]
        )
        relationships = sorted(relationships, key=lambda relationship: relationship.relationship_id)
        click.echo(_dump_relationships(relationships))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@entities_cli.command("summary")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
def entities_summary(scope: Optional[Path]):
    """Summarize the generated architecture corpus for the current scope."""
    try:
        repository = _load_architecture_repository(scope)
        click.echo(
            _dump_yaml(repository.get_corpus_summary().model_dump(mode="json", exclude_none=True))
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@entities_cli.command("invariants")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option("--adr", "adr_id", help="Filter by ADR reference")
@click.option("--domain", help="Filter by domain")
@click.option(
    "--status",
    type=click.Choice(["proposed", "active", "deprecated", "superseded"]),
    help="Filter by lifecycle stage",
)
def entities_invariants(
    scope: Optional[Path], adr_id: Optional[str], domain: Optional[str], status: Optional[str]
):
    """List invariants from the generated registry."""
    try:
        repository = _load_architecture_repository(scope)
        entities = repository.query_entities(
            entity_type="invariant",
            adr=adr_id,
            domain=domain,
            status=status,
        )
        click.echo(_dump_entities(entities))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@entities_cli.command("capabilities")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option("--adr", "adr_id", help="Filter by ADR reference")
@click.option("--domain", help="Filter by domain")
@click.option(
    "--status",
    type=click.Choice(["proposed", "active", "deprecated", "superseded"]),
    help="Filter by lifecycle stage",
)
def entities_capabilities(
    scope: Optional[Path], adr_id: Optional[str], domain: Optional[str], status: Optional[str]
):
    """List capabilities from the generated registry."""
    try:
        repository = _load_architecture_repository(scope)
        entities = repository.query_entities(
            entity_type="capability",
            adr=adr_id,
            domain=domain,
            status=status,
        )
        click.echo(_dump_entities(entities))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("scope")
@click.option("--recursive", is_flag=True, help="Show all sub-module scopes")
def show_scope(recursive: bool):
    """Show detected project scope(s) (ADR-L-0002: CAP-0001).

    Displays project boundaries and ADR directory locations.
    """
    try:
        resolver = ProjectScopeResolver()

        if recursive:
            scopes = resolver.resolve_recursive()
            click.echo(f"Found {len(scopes)} project scope(s):\n")

            for i, scope in enumerate(scopes, 1):
                marker_info = f" (via {scope.marker})" if scope.marker != "auto-detected" else ""
                sub_info = " [sub-module]" if scope.is_sub_module else " [workspace root]"

                click.echo(f"{i}. {scope.name}{sub_info}{marker_info}")
                click.echo(f"   Root: {scope.root}")
                click.echo(f"   ADRs: {scope.adr_dir}")

                if scope.adr_dir.exists():
                    logical_count = (
                        len(list((scope.adr_dir / "logical").glob("*.yaml")))
                        if (scope.adr_dir / "logical").exists()
                        else 0
                    )
                    physical_count = (
                        len(list((scope.adr_dir / "physical").glob("*.yaml")))
                        if (scope.adr_dir / "physical").exists()
                        else 0
                    )
                    physical_system_count = (
                        len(list(scope.physical_system_dir.glob("*.yaml")))
                        if scope.physical_system_dir.exists()
                        else 0
                    )
                    physical_component_count = (
                        len(list(scope.physical_component_dir.glob("*.yaml")))
                        if scope.physical_component_dir.exists()
                        else 0
                    )
                    click.echo(
                        "   ADR count: "
                        f"{logical_count} logical, "
                        f"{physical_count} physical, "
                        f"{physical_system_count} physical-system, "
                        f"{physical_component_count} physical-component"
                    )
                else:
                    click.echo("   ADR count: (directory not found)")

                click.echo()
        else:
            scope = resolver.resolve()
            marker_info = f" (detected via {scope.marker})" if scope.marker != "explicit" else ""

            click.echo(f"Project: {scope.name}{marker_info}")
            click.echo(f"Root: {scope.root}")
            click.echo(f"ADR directory: {scope.adr_dir}")
            click.echo(f"Manifest: {scope.manifest_path}")

            if scope.is_sub_module and scope.parent_scope:
                click.echo(f"\nParent project: {scope.parent_scope.name}")
                click.echo(f"Parent root: {scope.parent_scope.root}")

            if scope.adr_dir.exists():
                logical_count = (
                    len(list((scope.adr_dir / "logical").glob("*.yaml")))
                    if (scope.adr_dir / "logical").exists()
                    else 0
                )
                physical_count = (
                    len(list((scope.adr_dir / "physical").glob("*.yaml")))
                    if (scope.adr_dir / "physical").exists()
                    else 0
                )
                physical_system_count = (
                    len(list(scope.physical_system_dir.glob("*.yaml")))
                    if scope.physical_system_dir.exists()
                    else 0
                )
                physical_component_count = (
                    len(list(scope.physical_component_dir.glob("*.yaml")))
                    if scope.physical_component_dir.exists()
                    else 0
                )
                click.echo(
                    "\nADR count: "
                    f"{logical_count} logical, "
                    f"{physical_count} physical, "
                    f"{physical_system_count} physical-system, "
                    f"{physical_component_count} physical-component"
                )
            else:
                click.echo("\nADR directory does not exist")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("validate-project-metadata")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope root (used with --recursive).",
)
@click.option(
    "--file",
    "file_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("PROJECT.yaml"),
    show_default=True,
    help="Path to the PROJECT.yaml file.",
)
@click.option(
    "--recursive", is_flag=True, help="Validate PROJECT.yaml for all detected scopes recursively."
)
def validate_project_metadata(scope: Optional[Path], file_path: Path, recursive: bool):
    """Validate PROJECT.yaml against schema and model rules."""
    try:
        parser = ADRParser()
        failures = 0
        if recursive:
            for index, current_scope in enumerate(_ordered_scopes(scope)):
                current_file = current_scope.root / "PROJECT.yaml"
                if index:
                    click.echo()
                click.echo(f"Project scope: {current_scope.name} ({current_scope.root})")
                try:
                    project = parser.parse_project_metadata(current_file)
                    click.echo(f"PROJECT.yaml valid: {current_file}")
                    click.echo(f"  Project: {project.project.name}")
                    click.echo(f"  Team: {project.ownership.team}")
                except Exception as exc:
                    failures += 1
                    click.echo(f"ERROR: {current_file}: {exc}", err=True)
        else:
            project = parser.parse_project_metadata(file_path)
            click.echo(f"PROJECT.yaml valid: {file_path}")
            click.echo(f"  Project: {project.project.name}")
            click.echo(f"  Team: {project.ownership.team}")

        if failures:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("audit-runtime")
@click.option(
    "--requirements",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("requirements.txt"),
    show_default=True,
    help="Requirements file for dependency security audit.",
)
@click.option(
    "--pyproject",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("pyproject.toml"),
    show_default=True,
    help="pyproject.toml used to determine direct dependencies.",
)
@click.option(
    "--fail-on-outdated/--warn-on-outdated",
    default=False,
    show_default=True,
    help="Whether outdated direct dependencies fail the command.",
)
def audit_runtime(requirements: Path, pyproject: Path, fail_on_outdated: bool):
    """Audit deprecated APIs and dependency posture."""
    failures = 0

    click.echo("Checking deprecated runtime APIs...")
    deprecations = find_import_deprecations("adr_kit")
    if deprecations:
        failures += 1
        click.echo("Deprecated API usage detected:", err=True)
        for line in format_findings(deprecations):
            click.echo(f"  - {line}", err=True)
    else:
        click.echo("  OK: no deprecation warnings during adr_kit import scan")

    click.echo("\nChecking dependency security...")
    audit_result = run_pip_audit(requirements)
    if audit_result.returncode != 0:
        failures += 1
        click.echo("Dependency security audit failed:", err=True)
        if audit_result.stdout.strip():
            click.echo(audit_result.stdout.strip(), err=True)
        if audit_result.stderr.strip():
            click.echo(audit_result.stderr.strip(), err=True)
    else:
        click.echo("  OK: no known vulnerabilities in audited dependencies")

    click.echo("\nChecking direct dependency freshness...")
    direct_dependencies = load_direct_dependency_names(requirements, pyproject)
    outdated = list_outdated_packages(direct_dependencies)
    if outdated:
        click.echo("Outdated direct dependencies detected:")
        for line in format_outdated_packages(outdated):
            click.echo(f"  - {line}")
        if fail_on_outdated:
            failures += 1
    else:
        click.echo("  OK: direct dependencies are current")

    if failures:
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("generate-system-overview")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to write the generated system overview (default: <scope>/SYSTEM-OVERVIEW.md).",
)
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
def generate_system_overview(output: Optional[Path], scope: Optional[Path]):
    """Generate the AI-first SYSTEM-OVERVIEW.md artifact for one scope."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        detected = resolver.resolve()
        frontend = run_frontend_pipeline(scope=detected)
        generator = SystemOverviewGenerator(scope=detected, build_result=frontend)
        destination = output or (detected.root / "SYSTEM-OVERVIEW.md")
        generator.save(destination)
        click.echo(f"Generated system overview: {destination}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0007")
@cli.command("generate-adr-projection")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--recursive", is_flag=True, help="Generate ADR human projections for all scopes recursively"
)
def generate_adr_projection(scope: Optional[Path], recursive: bool):
    """Generate ADR human projection markdown under adrs/adr-projection/."""
    _generate_adr_projection_docs(scope=scope, recursive=recursive, label="ADR projection")


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0007")
@cli.command("generate-rendered-docs")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--recursive", is_flag=True, help="Generate ADR human projections for all scopes recursively"
)
def generate_rendered_docs(scope: Optional[Path], recursive: bool):
    """Compatibility alias for generate-adr-projection."""
    _generate_adr_projection_docs(scope=scope, recursive=recursive, label="rendered docs")


def _generate_adr_projection_docs(*, scope: Optional[Path], recursive: bool, label: str) -> None:
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        compiler = ArchitectureCompiler(scope_resolver=resolver)
        if recursive:
            workspace_result = compiler.compile_recursive(
                config=CompilerConfig(emit={"markdown"}, include_system_overview=False),
            )
            if not workspace_result.success:
                raise ValueError("Architecture compilation failed")
            total = 0
            for scoped in workspace_result.scope_results:
                click.echo(f"Generating {label} for {scoped.scope.name}...")
                markdown_artifacts = sorted(
                    (
                        artifact
                        for artifact in scoped.result.artifacts
                        if artifact.kind == "markdown"
                    ),
                    key=lambda artifact: artifact.path.as_posix(),
                )
                for artifact in markdown_artifacts:
                    click.echo(f"  Generated: {scoped.scope.root / artifact.path}")
                total += len(markdown_artifacts)
            click.echo(f"\nGenerated {total} ADR human projection artifact(s)")
        else:
            detected_scope = resolver.resolve()
            click.echo(f"Generating {label} for {detected_scope.name}...")
            result = compiler.compile(
                detected_scope,
                CompilerConfig(emit={"markdown"}, include_system_overview=False),
            )
            if not result.success:
                raise ValueError("Architecture compilation failed")
            markdown_artifacts = sorted(
                (artifact for artifact in result.artifacts if artifact.kind == "markdown"),
                key=lambda artifact: artifact.path.as_posix(),
            )
            for artifact in markdown_artifacts:
                click.echo(f"  Generated: {detected_scope.root / artifact.path}")
            click.echo(f"\nGenerated {len(markdown_artifacts)} ADR human projection artifact(s)")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("validate-system-overview")
@click.option(
    "--file",
    "file_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("SYSTEM-OVERVIEW.md"),
    show_default=True,
    help="Path to the system overview file.",
)
def validate_system_overview(file_path: Path):
    """Validate that SYSTEM-OVERVIEW.md is generated and current."""
    try:
        result = SystemOverviewValidator(
            generator=SystemOverviewGenerator(repo_root=Path.cwd())
        ).validate_file(file_path)
        if result.errors:
            for error in result.errors:
                click.echo(f"ERROR: {error}", err=True)
            sys.exit(1)
        for warning in result.warnings:
            click.echo(f"WARNING: {warning}")
        click.echo(f"System overview is valid: {file_path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013")
@cli.command("validate-generated-docs")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Explicit project scope (overrides auto-detection)",
)
@click.option(
    "--recursive", is_flag=True, help="Validate generated documentation for all scopes recursively"
)
def validate_generated_docs(scope: Optional[Path], recursive: bool):
    """Validate covered generated documentation artifacts."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        validator = GeneratedArtifactValidator(scope_resolver=resolver)
        results_by_scope = (
            validator.validate_recursive()
            if recursive
            else {
                resolver.resolve().name
                or str(resolver.resolve().root): validator.validate_scope(resolver.resolve())
            }
        )

        failures = 0
        for scope_name, results in results_by_scope.items():
            click.echo(f"{scope_name}:")
            for result in results:
                click.echo(f"  {result.status}: {result.artifact_path} " f"({result.reason_code})")
                if result.status != GeneratedArtifactStatus.VALID.value:
                    failures += 1

        if failures:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _resolve_attribution_evidence_path(scope_root: Path, evidence: Optional[Path]) -> Path:
    """Return path to attribution evidence YAML, resolving defaults under scope_root."""
    if evidence is not None:
        resolved = Path(evidence).expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Attribution evidence not found: {resolved}")
        return resolved
    candidates = [
        scope_root / "state" / "attribution" / "implementation-attribution-evidence.yaml",
        scope_root / ".ste" / "state" / "attribution" / "implementation-attribution-evidence.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "No attribution evidence file found.\nProvide --evidence or place file at:\n"
        + "\n".join(str(c) for c in candidates),
    )


def _coverage_from_v15(
    evidence: ImplementationAttributionEvidenceV15 | ImplementationAttributionEvidenceV16,
    repo: ArchitectureRepository,
) -> tuple[list[str], dict[str, int], dict[str, int], dict[str, int]]:
    unique_edges = unique_semantic_edges(evidence)
    unique_by_relationship = {"implements": 0, "enforces": 0, "embodies": 0}
    unique_by_type: dict[str, int] = {}
    cited: set[str] = set()
    for _impl, relationship, target in unique_edges:
        unique_by_relationship[relationship] = unique_by_relationship.get(relationship, 0) + 1
        entity = repo.find_entity_by_uuid(target)
        if entity is None:
            continue
        unique_by_type[entity.entity_type] = unique_by_type.get(entity.entity_type, 0) + 1
        if entity.entity_type == "adr" and entity.alias_id:
            cited.add(entity.alias_id)
    return (
        sorted(cited),
        unique_by_relationship,
        unique_by_type,
        relationship_occurrence_counts(evidence),
    )


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0004")
@cli.group("attribution")
def attribution_cli():
    """Implementation attribution evidence helpers."""
    pass


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0004")
@attribution_cli.command("check")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root (defaults to cwd). Must contain canonical /adrs for validation.",
)
@click.option(
    "--evidence",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Path to implementation-attribution-evidence.yaml. "
        "Defaults to state/attribution/ or .ste/state/attribution/ under --scope."
    ),
)
@click.option(
    "--profile",
    type=click.Choice(["greenfield", "brownfield", "migration"]),
    default="greenfield",
    show_default=True,
)
def attribution_check_cmd(scope: Optional[Path], evidence: Optional[Path], profile: str):
    """Validate implementation attribution evidence against the canonical ADR corpus."""
    try:
        scope_root = Path(scope).resolve() if scope else Path.cwd().resolve()
        ev_path = _resolve_attribution_evidence_path(scope_root, evidence)
        parser = ADRParser()
        evidence_obj = parser.parse_implementation_attribution_evidence(ev_path)

        repo = ArchitectureRepository(project_root=scope_root)
        repo.load()

        typed_profile = cast(ContractProfile, profile)
        result = validate_implementation_attribution_evidence(
            repo,
            evidence_obj,
            profile=typed_profile,
        )
        click.echo(
            yaml.safe_dump(
                {
                    "evidence_file": str(ev_path),
                    "schema_version": evidence_obj.schema_version,
                    "record_count": len(evidence_obj.records),
                    "profile": result.profile,
                    "outcome": result.outcome,
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                    "issues": [
                        {"severity": i.severity, "path": i.path, "message": i.message}
                        for i in result.issues
                    ],
                },
                sort_keys=False,
                allow_unicode=True,
            ).rstrip()
        )
        if not result.is_valid:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0004")
@attribution_cli.command("coverage")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
)
@click.option("--evidence", type=click.Path(dir_okay=False, path_type=Path), default=None)
def attribution_coverage_cmd(scope: Optional[Path], evidence: Optional[Path]):
    """Report ADRs cited by attribution evidence vs ADR corpus (informational)."""
    try:
        scope_root = Path(scope).resolve() if scope else Path.cwd().resolve()
        cited: list[str] = []
        schema_version = "unknown"
        unique_by_relationship: dict[str, int] = {
            "implements": 0,
            "enforces": 0,
            "embodies": 0,
        }
        unique_by_type: dict[str, int] = {}
        occurrence_by_relationship: dict[str, int] = {
            "implements": 0,
            "enforces": 0,
            "embodies": 0,
        }
        validated_link_count = 0
        warning_link_count = 0
        rejected_claim_count = 0
        try:
            ev_path = _resolve_attribution_evidence_path(scope_root, evidence)
            parser = ADRParser()
            evidence_obj = parser.parse_implementation_attribution_evidence(ev_path)
            schema_version = str(evidence_obj.schema_version)
            repo = ArchitectureRepository(project_root=scope_root)
            repo.load()
            if isinstance(
                evidence_obj,
                (ImplementationAttributionEvidenceV15, ImplementationAttributionEvidenceV16),
            ):
                cited, unique_by_relationship, unique_by_type, occurrence_by_relationship = (
                    _coverage_from_v15(evidence_obj, repo)
                )
                from ..api import EmbodimentLinkageRequest, build_embodiment_linkage

                linkage = build_embodiment_linkage(
                    EmbodimentLinkageRequest(
                        project_root=scope_root,
                        evidence_path=ev_path,
                        profile="brownfield",
                    )
                )
                validated_link_count = len(linkage.links)
                warning_link_count = sum(
                    link.validation_status == "warning" for link in linkage.links
                )
                rejected_claim_count = len(linkage.rejected_claims)
            else:
                seen: set[str] = set()
                unique_edges: set[tuple[str, str, str]] = set()
                for rec in evidence_obj.records:
                    for adr_id in rec.attributed_adrs:
                        seen.add(adr_id)
                        unique_edges.add((rec.implementation_entity_id, "implements", adr_id))
                        occurrence_by_relationship["implements"] += 1
                    for inv_id in rec.enforced_invariants:
                        unique_edges.add((rec.implementation_entity_id, "enforces", inv_id))
                        occurrence_by_relationship["enforces"] += 1
                    for cap_id in rec.attributed_capabilities:
                        unique_edges.add((rec.implementation_entity_id, "implements", cap_id))
                        occurrence_by_relationship["implements"] += 1
                cited = sorted(seen)
                for _impl, rel, _target in unique_edges:
                    unique_by_relationship[rel] = unique_by_relationship.get(rel, 0) + 1
        except FileNotFoundError:
            repo = ArchitectureRepository(project_root=scope_root)
            repo.load()

        repo = ArchitectureRepository(project_root=scope_root)
        repo.load()
        if repo.model_version in {"2.0", "2.1", "2.2"}:
            if repo.model_version == "2.2":
                model_v2 = repo.get_model_v22()
            elif repo.model_version == "2.1":
                model_v2 = repo.get_model_v21()
            else:
                model_v2 = repo.get_model_v2()
            catalog = sorted(
                {
                    entity.alias_id
                    for entity in model_v2.entities
                    if entity.entity_type == "adr" and entity.alias_id
                }
            )
        else:
            catalog = sorted(repo.get_model().adr_status_map().keys())
        unattributed_in_corpus = sorted(set(catalog) - set(cited))

        payload = {
            "scope_root": str(scope_root),
            "evidence_schema_version": schema_version,
            "adrs_with_attribution_claims": cited,
            "adr_corpus_total": len(catalog),
            "catalog_adrs_not_cited_by_evidence": unattributed_in_corpus,
            "semantic_unique_claim_counts_by_relationship": {
                key: unique_by_relationship.get(key, 0)
                for key in ("implements", "enforces", "embodies")
            },
            "semantic_unique_claim_counts_by_resolved_target_entity_type": dict(
                sorted(unique_by_type.items())
            ),
            "semantic_evidence_occurrence_counts_by_relationship": {
                key: occurrence_by_relationship.get(key, 0)
                for key in ("implements", "enforces", "embodies")
            },
            "validated_semantic_link_count": validated_link_count,
            "warning_semantic_link_count": warning_link_count,
            "rejected_semantic_claim_count": rejected_claim_count,
        }
        click.echo(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).rstrip())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0012", "ADR-L-0013", "ADR-L-0004")
@attribution_cli.command("workspace-report")
@click.option(
    "--workspace-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    show_default=True,
    help="Directory containing workspace.yaml (or parent of output_dir).",
)
@click.option(
    "--state-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Override derived state directory (default: output_dir from workspace.yaml).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Federation YAML path (default: <state-dir>/workspace-attribution-federation.yaml).",
)
def attribution_workspace_report_cmd(
    workspace_root: Path,
    state_dir: Optional[Path],
    output: Optional[Path],
):
    """Build workspace attribution federation index (qualified ADR ids across repos)."""
    try:
        resolved_state, repos = resolve_workspace_repos(Path(workspace_root))
        state_path = Path(state_dir).resolve() if state_dir is not None else resolved_state
        out_path = (
            Path(output).resolve()
            if output is not None
            else state_path / "workspace-attribution-federation.yaml"
        )
        write_workspace_attribution_federation(
            out_path,
            workspace_root=Path(workspace_root).resolve(),
            state_dir=state_path,
            repos=repos,
        )
        doc = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        homonym_count = len(doc.get("homonym_groups") or [])
        qualified_count = len(doc.get("qualified_adrs") or [])
        click.echo(
            yaml.safe_dump(
                {
                    "output": str(out_path),
                    "qualified_adr_count": qualified_count,
                    "homonym_group_count": homonym_count,
                    "repos_scanned": [name for name, _ in repos],
                },
                sort_keys=False,
            ).rstrip(),
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0004", "ADR-L-0020")
@attribution_cli.command("normalize-evidence")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Project root used to resolve aliases and UUIDs.",
)
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Attribution evidence YAML to normalize.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write canonical evidence to this path. Omit to print to stdout.",
)
@click.option(
    "--target-version",
    type=click.Choice(["1.5", "1.6"]),
    default="1.5",
    show_default=True,
    help="Canonical evidence target; v1.5 remains the compatibility default.",
)
def attribution_normalize_evidence_cmd(
    scope: Path,
    input_path: Path,
    output: Optional[Path],
    target_version: str,
) -> None:
    """Normalize supported evidence losslessly. Does not write by default."""
    try:
        parser = ADRParser()
        evidence_obj = parser.parse_implementation_attribution_evidence(input_path)
        repo = ArchitectureRepository(project_root=Path(scope).resolve())
        repo.load()
        canonical = normalize_attribution_evidence(
            evidence_obj,
            repo,
            target_version=target_version,
        )
        payload = evidence_to_canonical_dict(canonical)
        rendered = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
        if output is None:
            click.echo(rendered.rstrip())
            return
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        click.echo(f"Wrote canonical v{target_version} evidence: {output_path.resolve()}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@implements_adr("ADR-L-0004", "ADR-L-0020", "ADR-PC-0007")
@attribution_cli.command("linkage-report")
@click.option(
    "--scope",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--evidence",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--profile",
    type=click.Choice(["greenfield", "brownfield", "migration"]),
    default="greenfield",
    show_default=True,
)
@click.option("--implementation-entity-id", default=None)
@click.option("--intent-entity-id", default=None)
@click.option(
    "--relationship", type=click.Choice(["implements", "enforces", "embodies"]), default=None
)
def attribution_linkage_report_cmd(
    scope: Path,
    evidence: Path,
    profile: str,
    implementation_entity_id: Optional[str],
    intent_entity_id: Optional[str],
    relationship: Optional[str],
) -> None:
    """Build a deterministic, non-authoritative embodiment linkage report."""
    if implementation_entity_id and intent_entity_id:
        raise click.UsageError(
            "--implementation-entity-id and --intent-entity-id are mutually exclusive"
        )
    from ..api import EmbodimentLinkageRequest, build_embodiment_linkage

    result = build_embodiment_linkage(
        EmbodimentLinkageRequest(
            project_root=scope,
            evidence_path=evidence,
            profile=cast(ContractProfile, profile),
        )
    )
    links = result.links
    if implementation_entity_id:
        links = result.links_for_implementation(implementation_entity_id)
    elif intent_entity_id:
        links = result.implementations_for_intent(intent_entity_id)
    if relationship:
        links = tuple(link for link in links if link.relationship == relationship)

    def provenance_payload(value: LinkageProvenance) -> dict[str, object]:
        return {
            key: item
            for key, item in {
                "source_file": value.source_file,
                "source_pointer": value.source_pointer,
                "start_line": value.start_line,
                "end_line": value.end_line,
                "extractor": value.extractor,
                "commit": value.commit,
            }.items()
            if item is not None
        }

    payload = {
        "evidence_file": str(result.request.evidence_path),
        "evidence_schema_version": result.evidence_schema_version,
        "success": result.success,
        "authority_ceiling": "validated_derived_evidence",
        "graph_admission_status": "not_admitted",
        "links": [
            {
                "implementation_entity_id": link.implementation_entity_id,
                "implementation_entity_type": link.implementation_entity_type,
                "relationship": link.relationship,
                "target_entity_id": link.target_entity_id,
                "target_entity_type": link.target_entity_type,
                "target_alias_id": link.target_alias_id,
                "target_alias_name": link.target_alias_name,
                "target_lifecycle": link.target_lifecycle,
                "validation_status": link.validation_status,
                "occurrences": [
                    {
                        "confidence": occurrence.confidence,
                        "provenance": provenance_payload(occurrence.provenance),
                    }
                    for occurrence in link.occurrences
                ],
            }
            for link in links
        ],
        "rejected_claims": [
            {
                "implementation_entity_id": item.implementation_entity_id,
                "relationship": item.relationship,
                "target_entity_id": item.target_entity_id,
                "confidence": item.confidence,
                "provenance": provenance_payload(item.provenance),
                "diagnostics": [diagnostic.message for diagnostic in item.diagnostics],
            }
            for item in result.rejected_claims
        ],
        "error_count": result.error_count,
        "warning_count": result.warning_count,
    }
    click.echo(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).rstrip())
    if not result.success:
        raise click.exceptions.Exit(1)


@implements_adr("ADR-L-0002", "ADR-L-0013", "ADR-L-0004")
@attribution_cli.command("generate-shim")
@click.option(
    "--lang",
    "--language",
    "language",
    type=click.Choice(["python", "typescript"], case_sensitive=False),
    required=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write shim to path; omit to print to stdout.",
)
def attribution_generate_shim(language: str, output: Optional[Path]):
    """Emit a standalone no-op implementation-linkage shim (Python or TypeScript)."""
    try:
        body = generate_shim(language)
        if output is None:
            click.echo(body)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(body, encoding="utf-8")
            click.echo(f"Wrote {language} shim: {output.resolve()}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group("promote")
def promote_group() -> None:
    """Design Journal Promotion Contract operations (thin adapter over adr_kit.api)."""


@promote_group.command("prepare")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    show_default=True,
)
@click.option(
    "--contract",
    "promotion_contract_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--output",
    "prepared_contract_output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
)
def promote_prepare(
    project_root: Path,
    promotion_contract_path: Path,
    prepared_contract_output_path: Optional[Path],
) -> None:
    """Prepare a Promotion Contract without mutating canonical authority."""

    from ..api import PromotionPrepareRequest, prepare_promotion

    result = prepare_promotion(
        PromotionPrepareRequest(
            project_root=project_root,
            promotion_contract_path=promotion_contract_path,
            prepared_contract_output_path=prepared_contract_output_path,
        )
    )
    click.echo(
        f"prepared={result.success} mechanical_ready={result.mechanical_promotion_ready} "
        f"baseline={result.baseline.equivalent} blockers={len(result.blockers)} "
        f"fingerprint={result.locked_intent_fingerprint}"
    )
    if result.prepared_contract_path:
        click.echo(f"prepared_contract_path={result.prepared_contract_path}")
    if not result.success:
        sys.exit(1)


@promote_group.command("check")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    show_default=True,
)
@click.option(
    "--contract",
    "promotion_contract_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
def promote_check(project_root: Path, promotion_contract_path: Path) -> None:
    """Check promotion readiness without authority writes."""

    from ..api import PromotionCheckRequest, check_promotion

    result = check_promotion(
        PromotionCheckRequest(
            project_root=project_root,
            promotion_contract_path=promotion_contract_path,
        )
    )
    click.echo(
        f"ok={result.success} mechanical_ready={result.mechanical_promotion_ready} "
        f"human_lock={result.human_lock_present} blockers={len(result.blockers)}"
    )
    if not result.success:
        sys.exit(1)


@promote_group.command("apply")
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    show_default=True,
)
@click.option(
    "--contract",
    "promotion_contract_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--commit", is_flag=True, help="Commit authority mutations (requires human_lock)")
@click.option("--timestamp", default=None, help="RFC3339 UTC timestamp ending in Z")
def promote_apply(
    project_root: Path,
    promotion_contract_path: Path,
    commit: bool,
    timestamp: Optional[str],
) -> None:
    """Dry-run or commit a locked prepared Promotion Contract."""

    from ..api import PromotionApplyRequest, apply_promotion

    result = apply_promotion(
        PromotionApplyRequest(
            project_root=project_root,
            promotion_contract_path=promotion_contract_path,
            commit=commit,
            timestamp=timestamp,
        )
    )
    click.echo(
        f"success={result.success} state={result.semantic_state} "
        f"authority_committed={result.authority_committed} "
        f"evidence={result.apply_execution_evidence_appended} "
        f"regen={result.regeneration_completed} validation={result.validation_success}"
    )
    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    cli()
