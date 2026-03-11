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

from ..generators import ManifestGenerator
from ..validators import ADRValidator
from ..scope import ProjectScopeResolver


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
                generator.save_manifest(manifest, output_path)
                click.echo(f"Generated manifest for {scope_name}: {output_path}")
            
            click.echo(f"\nGenerated {len(manifests)} manifests")
        else:
            click.echo("Generating manifest...")
            detected_scope = resolver.resolve()
            click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")
            
            manifest = generator.generate_from_scope(detected_scope)
            output_path = output or detected_scope.manifest_path
            generator.save_manifest(manifest, output_path)
            
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
                    click.echo(f"  ✗ {errors} files with errors", fg='red')
                if warnings > 0:
                    click.echo(f"  ⚠ {warnings} files with warnings", fg='yellow')
                if errors == 0 and warnings == 0:
                    click.echo(f"  All {len(results)} files valid", fg='green')
                
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
                    click.echo(f"\n✗ {file_path}", fg='red')
                    for error in result.errors:
                        click.echo(f"  ERROR: {error.message}")
                    errors += 1
                elif result.has_warnings:
                    click.echo(f"\n⚠ {file_path}", fg='yellow')
                    for warning in result.warnings:
                        click.echo(f"  WARNING: {warning.message}")
                    warnings += 1
            
            if errors == 0 and warnings == 0:
                click.echo(f"All {len(results)} files valid", fg='green')
            else:
                click.echo(f"\n{len(results)} files: {errors} errors, {warnings} warnings")
            
            # Validate cross-references if requested
            if cross_references:
                click.echo("\nValidating cross-references...")
                xref_result = validator.validate_cross_references(detected_scope.adr_dir)
                
                if xref_result.has_errors:
                    click.echo("✗ Cross-reference validation failed", fg='red')
                    for error in xref_result.errors:
                        click.echo(f"  ERROR: {error.message}")
                    sys.exit(1)
                else:
                    click.echo("Cross-references valid", fg='green')
            
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


if __name__ == '__main__':
    cli()
