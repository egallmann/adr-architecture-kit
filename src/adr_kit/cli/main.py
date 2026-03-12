"""CLI for ADR toolkit.

Implements ADR-L-0002: Multi-scope ADR architecture with scope-aware commands.
"""

import sys
from pathlib import Path
from typing import Optional

try:
    import click
except ImportError:
    print("Error: click package not installed. Install with: pip install adr-architecture-kit[cli]")
    sys.exit(1)

from ..generators import ManifestGenerator, PhysicalSystemADRGenerator, SystemOverviewGenerator
from ..generators.views import MarkdownGenerator
from ..integrity import GeneratedArtifactStatus
from ..parser import ADRParser
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
)
from ..scope import ProjectScopeResolver


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
        files.extend(sorted(path for path in directory.glob("*.yaml") if path.is_file() and not path.is_symlink()))
    return files


@click.group()
@click.version_option()
def cli():
    """ADR Architecture Kit - Multi-scope ADR management."""
    pass


@cli.command('generate-manifest')
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
@click.option('--recursive', is_flag=True,
              help='Generate manifests for all sub-modules recursively')
@click.option('--output', type=click.Path(path_type=Path),
              help='Output path for manifest (default: <scope>/adrs/manifest.yaml)')
def generate_manifest(scope: Optional[Path], recursive: bool, output: Optional[Path]):
    """Generate manifest.yaml from ADRs (ADR-L-0002: CAP-0002).
    
    Auto-detects project scope by default. Use --scope to override.
    Use --recursive to generate manifests for all sub-modules.
    """
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        generator = ManifestGenerator(scope_resolver=resolver)
        
        if recursive:
            click.echo("Generating manifests recursively...")
            manifests = generator.generate_recursive()
            
            for scope_name, manifest in manifests.items():
                scope_obj = next(s for s in resolver.resolve_recursive() if s.name == scope_name)
                output_path = output or scope_obj.manifest_path
                generator.save_manifest(manifest, output_path, scope_obj)
                click.echo(f"Generated manifest for {scope_name}: {output_path}")
            
            click.echo(f"\nGenerated {len(manifests)} manifests")
        else:
            click.echo("Generating manifest...")
            detected_scope = resolver.resolve()
            click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")
            
            manifest = generator.generate_from_scope(detected_scope)
            output_path = output or detected_scope.manifest_path
            generator.save_manifest(manifest, output_path, detected_scope)
            
            click.echo(f"Generated manifest: {output_path}")
            click.echo(f"  ADRs: {manifest.statistics.total_adrs}")
            click.echo(f"  Logical: {manifest.statistics.logical_adrs}")
            click.echo(f"  Physical: {manifest.statistics.physical_adrs}")
            if manifest.statistics.physical_system_adrs > 0:
                click.echo(f"  Physical-System: {manifest.statistics.physical_system_adrs}")
            if manifest.statistics.physical_component_adrs > 0:
                click.echo(f"  Physical-Component: {manifest.statistics.physical_component_adrs}")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("generate-physical-system")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured YAML input for the Physical-System ADR.",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to write the generated Physical-System ADR YAML.",
)
def generate_physical_system(input_path: Path, output: Path):
    """Generate a Physical-System ADR YAML file from structured input."""
    try:
        parser = ADRParser()
        validator = ADRValidator(parser=parser)
        generator = PhysicalSystemADRGenerator(parser=parser, validator=validator)

        adr = generator.create_adr_from_file(input_path)
        generator.save_adr(adr, output)

        parser.parse_physical_system_adr(output)
        result = validator.validate_file(output)

        if result.has_errors:
            click.echo(f"Generated file failed validation: {output}", err=True)
            for error in result.errors:
                click.echo(f"  ERROR: {error.message}", err=True)
            sys.exit(1)

        click.echo(f"Generated Physical-System ADR: {output}")
        click.echo(f"  ID: {adr.id}")
        click.echo(f"  Title: {adr.title}")

        if result.has_warnings:
            for warning in result.warnings:
                click.echo(f"  WARNING: {warning.message}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('validate')
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
@click.option('--recursive', is_flag=True,
              help='Validate all sub-modules recursively')
@click.option('--cross-references', is_flag=True,
              help='Validate cross-references between ADRs')
def validate(scope: Optional[Path], recursive: bool, cross_references: bool):
    """Validate ADRs against schema and business rules (ADR-L-0002: CAP-0003).
    
    Auto-detects project scope by default. Use --scope to override.
    Use --recursive to validate all sub-modules (ADR-L-0002: INV-0019).
    """
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        validator = ADRValidator(scope_resolver=resolver)
        
        if recursive:
            click.echo("Validating ADRs recursively...")
            all_results = validator.validate_recursive()
            
            total_files = 0
            total_errors = 0
            total_warnings = 0
            
            for scope_name, results in all_results.items():
                click.echo(f"\n{scope_name}:")
                
                errors = sum(1 for r in results.values() if r.has_errors)
                warnings = sum(1 for r in results.values() if r.has_warnings)
                
                if errors > 0:
                    click.secho(f"  ERROR {errors} files with errors", fg='red')
                if warnings > 0:
                    click.secho(f"  WARN {warnings} files with warnings", fg='yellow')
                if errors == 0 and warnings == 0:
                    click.secho(f"  All {len(results)} files valid", fg="green")
                
                total_files += len(results)
                total_errors += errors
                total_warnings += warnings
            
            click.echo(f"\nTotal: {total_files} files, {total_errors} errors, {total_warnings} warnings")
            
            if total_errors > 0:
                sys.exit(1)
                
        else:
            click.echo("Validating ADRs...")
            detected_scope = resolver.resolve()
            click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")
            
            results = validator.validate_scope(detected_scope)
            
            # Print results
            errors = 0
            warnings = 0
            
            for file_path, result in results.items():
                if result.has_errors:
                    click.secho(f"\nERROR {file_path}", fg='red')
                    for error in result.errors:
                        click.echo(f"  ERROR: {error.message}")
                    errors += 1
                elif result.has_warnings:
                    click.secho(f"\nWARN {file_path}", fg='yellow')
                    for warning in result.warnings:
                        click.echo(f"  WARNING: {warning.message}")
                    warnings += 1
            
            if errors == 0 and warnings == 0:
                click.secho(f"All {len(results)} files valid", fg="green")
            else:
                click.echo(f"\n{len(results)} files: {errors} errors, {warnings} warnings")
            
            # Validate cross-references if requested
            if cross_references:
                click.echo("\nValidating cross-references...")
                xref_result = validator.validate_cross_references(detected_scope.adr_dir)
                
                if xref_result.has_errors:
                    click.secho("ERROR Cross-reference validation failed", fg='red')
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


@cli.command('scope')
@click.option('--recursive', is_flag=True,
              help='Show all sub-module scopes')
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
                marker_info = f" (via {scope.marker})" if scope.marker != 'auto-detected' else ""
                sub_info = " [sub-module]" if scope.is_sub_module else " [workspace root]"
                
                click.echo(f"{i}. {scope.name}{sub_info}{marker_info}")
                click.echo(f"   Root: {scope.root}")
                click.echo(f"   ADRs: {scope.adr_dir}")
                
                if scope.adr_dir.exists():
                    logical_count = len(list((scope.adr_dir / 'logical').glob('*.yaml'))) if (scope.adr_dir / 'logical').exists() else 0
                    physical_count = len(list((scope.adr_dir / 'physical').glob('*.yaml'))) if (scope.adr_dir / 'physical').exists() else 0
                    click.echo(f"   ADR count: {logical_count} logical, {physical_count} physical")
                else:
                    click.echo(f"   ADR count: (directory not found)")
                
                click.echo()
        else:
            scope = resolver.resolve()
            marker_info = f" (detected via {scope.marker})" if scope.marker != 'explicit' else ""
            
            click.echo(f"Project: {scope.name}{marker_info}")
            click.echo(f"Root: {scope.root}")
            click.echo(f"ADR directory: {scope.adr_dir}")
            click.echo(f"Manifest: {scope.manifest_path}")
            
            if scope.is_sub_module and scope.parent_scope:
                click.echo(f"\nParent project: {scope.parent_scope.name}")
                click.echo(f"Parent root: {scope.parent_scope.root}")
            
            if scope.adr_dir.exists():
                logical_count = len(list((scope.adr_dir / 'logical').glob('*.yaml'))) if (scope.adr_dir / 'logical').exists() else 0
                physical_count = len(list((scope.adr_dir / 'physical').glob('*.yaml'))) if (scope.adr_dir / 'physical').exists() else 0
                click.echo(f"\nADR count: {logical_count} logical, {physical_count} physical")
            else:
                click.echo(f"\nADR directory does not exist")
                
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


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


@cli.command("generate-system-overview")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("SYSTEM-OVERVIEW.md"),
    show_default=True,
    help="Path to write the generated system overview.",
)
def generate_system_overview(output: Path):
    """Generate the AI-first SYSTEM-OVERVIEW.md artifact."""
    try:
        generator = SystemOverviewGenerator()
        generator.save(output)
        click.echo(f"Generated system overview: {output}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("generate-rendered-docs")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
@click.option('--recursive', is_flag=True,
              help='Generate rendered ADR markdown for all scopes recursively')
def generate_rendered_docs(scope: Optional[Path], recursive: bool):
    """Generate rendered ADR markdown artifacts with integrity headers."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        parser = ADRParser()
        generator = MarkdownGenerator()
        scopes = resolver.resolve_recursive() if recursive else [resolver.resolve()]

        total = 0
        for current_scope in scopes:
            rendered_dir = current_scope.adr_dir / "rendered"
            rendered_dir.mkdir(parents=True, exist_ok=True)
            click.echo(f"Generating rendered docs for {current_scope.name}...")
            for source_path in _discover_scope_adr_files(current_scope):
                try:
                    adr = parser.parse_adr(source_path)
                    output_path = rendered_dir / f"{adr.id}.md"
                    generator.render_to_file(
                        adr,
                        output_path,
                        scope=current_scope,
                        source_path=source_path,
                    )
                    total += 1
                    click.echo(f"  Generated: {output_path}")
                except Exception as exc:
                    click.echo(f"  Warning: Failed to render {source_path.name}: {exc}")

        click.echo(f"\nGenerated {total} rendered ADR markdown artifact(s)")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


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
        result = SystemOverviewValidator().validate_file(file_path)
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


@cli.command("validate-generated-docs")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
@click.option('--recursive', is_flag=True,
              help='Validate generated documentation for all scopes recursively')
def validate_generated_docs(scope: Optional[Path], recursive: bool):
    """Validate covered generated documentation artifacts."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        validator = GeneratedArtifactValidator(scope_resolver=resolver)
        results_by_scope = (
            validator.validate_recursive() if recursive
            else {resolver.resolve().name or str(resolver.resolve().root): validator.validate_scope(resolver.resolve())}
        )

        failures = 0
        for scope_name, results in results_by_scope.items():
            click.echo(f"{scope_name}:")
            for result in results:
                click.echo(
                    f"  {result.status}: {result.artifact_path} "
                    f"({result.reason_code})"
                )
                if result.status != GeneratedArtifactStatus.VALID.value:
                    failures += 1

        if failures:
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
