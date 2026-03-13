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

import yaml

from ..generators import (
    ArchitectureIndexGenerator,
    EntityRegistryGenerator,
    LogicalADRGenerator,
    ManifestGenerator,
    PhysicalComponentADRGenerator,
    PhysicalSystemADRGenerator,
    SystemOverviewGenerator,
)
from ..generators.views import MarkdownGenerator
from ..integrity import GeneratedArtifactStatus
from ..migrators.canonical_id_normalizer import CanonicalIdNormalizer
from ..parser import ADRParser
from ..repository import ArchitectureRepository
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


def _architecture_index_path(scope) -> Path:
    """Return canonical architecture index output path for a scope."""
    return scope.adr_dir / "index" / "architecture-index.yaml"


def _load_architecture_repository(scope_path: Optional[Path]) -> ArchitectureRepository:
    """Load repository-backed architecture discovery state."""
    repository = ArchitectureRepository(scope_resolver=ProjectScopeResolver(explicit_scope=scope_path))
    repository.load()
    return repository


def _dump_yaml(data) -> str:
    """Render CLI output as deterministic YAML."""
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip()


def _entity_identifier(entity):
    return getattr(entity, "id", getattr(entity, "entity_id", None))


def _entity_type_name(entity):
    entity_type = getattr(entity, "entity_type", None)
    return entity_type.value if hasattr(entity_type, "value") else entity_type


def _entity_status(entity):
    lifecycle = getattr(entity, "lifecycle_stage", None)
    return lifecycle.value if hasattr(lifecycle, "value") else lifecycle


def _entity_adr_refs(entity):
    if hasattr(entity, "canonical_source"):
        refs = set()
        canonical_ref = entity.canonical_source.source_ref.split("#")[0]
        if canonical_ref.startswith("ADR-"):
            refs.add(canonical_ref)
        refs.update(
            ref.source_ref.split("#")[0]
            for ref in getattr(entity, "source_refs", []) or []
            if ref.source_ref.startswith("ADR-")
        )
        metadata = getattr(entity, "metadata", {}) or {}
        for metadata_ref_key in ("adr_id", "defined_in"):
            metadata_ref = metadata.get(metadata_ref_key)
            if metadata_ref and metadata_ref.startswith("ADR-"):
                refs.add(metadata_ref)
        refs.update(getattr(entity.relationships, "declared_in", []) or [])
        return refs
    refs = {getattr(entity, "introduced_by", "")}
    refs.update(getattr(entity, "related_adrs", []) or [])
    refs.update(getattr(entity, "realized_by", []) or [])
    return {ref for ref in refs if ref}


@click.group()
@click.version_option()
def cli():
    """ADR Architecture Kit - Multi-scope ADR management."""
    pass


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


@cli.command("generate-logical")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured YAML input for the Logical ADR.",
)
@click.option(
    "--output",
    required=True,
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
def generate_logical(
    input_path: Path,
    output: Path,
    validation_mode: str,
    preserve_empty_sections: bool,
):
    """Generate a Logical ADR YAML file from structured input."""
    try:
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


@cli.command("generate-vision")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured YAML input for the Vision ADR.",
)
@click.option(
    "--output",
    required=True,
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
def generate_vision(
    input_path: Path,
    output: Path,
    validation_mode: str,
    preserve_empty_sections: bool,
):
    """Generate a Vision ADR YAML file from structured input."""
    try:
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


@cli.command("generate-physical-component")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to structured YAML input for the Physical-Component ADR.",
)
@click.option(
    "--output",
    required=True,
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
def generate_physical_component(
    input_path: Path,
    output: Path,
    validation_mode: str,
    preserve_empty_sections: bool,
):
    """Generate a Physical-Component ADR YAML file from structured input."""
    try:
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
def generate_physical_system(
    input_path: Path,
    output: Path,
    validation_mode: str,
    preserve_empty_sections: bool,
):
    """Generate a Physical-System ADR YAML file from structured input."""
    try:
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


@cli.command("generate-entity-registry")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
@click.option('--recursive', is_flag=True,
              help='Generate entity registries for all sub-modules recursively')
@click.option('--output', type=click.Path(path_type=Path),
              help='Output path for registry (default: <scope>/adrs/entities/registry.yaml)')
def generate_entity_registry(scope: Optional[Path], recursive: bool, output: Optional[Path]):
    """Generate the legacy entity-registry.yaml compatibility artifact."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        generator = ArchitectureIndexGenerator(scope_resolver=resolver)

        if recursive:
            click.echo("Generating architecture indexes recursively for legacy entity registry compatibility...")
            scopes = resolver.resolve_recursive()
            for scope_obj in scopes:
                if not scope_obj.adr_dir.exists():
                    continue
                bundle = generator.generate_from_scope(scope_obj)
                paths = generator.save_bundle(bundle, scope_obj)
                scope_name = scope_obj.name or str(scope_obj.root)
                output_path = output or paths["legacy_entity_registry"]
                if output is not None and output_path != paths["legacy_entity_registry"]:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(
                        generator.render_yaml(bundle.legacy_entity_registry),
                        encoding="utf-8",
                        newline="\n",
                    )
                click.echo(f"Generated legacy entity registry for {scope_name}: {output_path}")
                click.echo(f"  Architecture index: {paths['architecture_index']}")

            click.echo(f"\nGenerated legacy entity registry compatibility artifacts for {len(scopes)} scope(s)")
        else:
            click.echo("Generating architecture index and legacy entity registry compatibility artifact...")
            detected_scope = resolver.resolve()
            click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")

            bundle = generator.generate_from_scope(detected_scope)
            paths = generator.save_bundle(bundle, detected_scope)
            output_path = output or paths["legacy_entity_registry"]
            if output is not None and output_path != paths["legacy_entity_registry"]:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    generator.render_yaml(bundle.legacy_entity_registry),
                    encoding="utf-8",
                    newline="\n",
                )

            click.echo(f"Generated legacy entity registry: {output_path}")
            click.echo(f"  Architecture index: {paths['architecture_index']}")
            click.echo(f"  Entities: {len(bundle.legacy_entity_registry.entities)}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("generate-architecture-index")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
def generate_architecture_index(scope: Optional[Path]):
    """Generate normalized architecture discovery artifacts under adrs/index/."""
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        generator = ArchitectureIndexGenerator(scope_resolver=resolver)
        detected_scope = resolver.resolve()
        click.echo("Generating architecture discovery index...")
        click.echo(f"Project scope: {detected_scope.name} ({detected_scope.root})")
        bundle = generator.generate_from_scope(detected_scope)
        paths = generator.save_bundle(bundle, detected_scope)
        click.echo(f"Generated architecture index: {_architecture_index_path(detected_scope)}")
        click.echo(f"  Namespace: {bundle.architecture_index.architecture_namespace}")
        click.echo(f"  Entities: {len(bundle.entity_registry.entities)}")
        click.echo(f"  Relationships: {len(bundle.relationship_registry.relationships)}")
        click.echo(f"  Unresolved: {len(bundle.unresolved_registry.unresolved)}")
        click.echo(f"  Legacy entity registry: {paths['legacy_entity_registry']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("normalize-canonical-ids")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
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
        click.echo(f"Migration ledger: {detected_scope.adr_dir / 'migrations' / 'canonical-id-remap.yaml'}")
        click.echo("Run `adr generate-architecture-index --scope .`")
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
@click.option(
    '--mode',
    type=click.Choice(["complete", "structural"]),
    default="complete",
    show_default=True,
    help='Validation mode to apply.'
)
def validate(scope: Optional[Path], recursive: bool, cross_references: bool, mode: str):
    """Validate ADRs against schema and business rules (ADR-L-0002: CAP-0003).
    
    Auto-detects project scope by default. Use --scope to override.
    Use --recursive to validate all sub-modules (ADR-L-0002: INV-0019).
    """
    try:
        resolver = ProjectScopeResolver(explicit_scope=scope)
        validator = ADRValidator(scope_resolver=resolver)
        
        if recursive:
            click.echo("Validating ADRs recursively...")
            all_results = validator.validate_recursive(mode=mode)
            
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
            
            results = validator.validate_scope(detected_scope, mode=mode)
            
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


@cli.group("entities")
def entities_cli():
    """Query the generated architecture discovery bundle."""
    pass


def _filter_entities(registry, entity_type=None, adr=None, domain=None, status=None):
    """Filter registry entities deterministically."""
    entities = sorted(registry.entities, key=_entity_identifier)
    if entity_type:
        entities = [entity for entity in entities if _entity_type_name(entity) == entity_type]
    if adr:
        entities = [entity for entity in entities if adr in _entity_adr_refs(entity)]
    if domain:
        entities = [entity for entity in entities if domain in ((getattr(entity, "domains", None) or getattr(entity, "metadata", {}).get("domains", [])) or [])]
    if status:
        entities = [entity for entity in entities if _entity_status(entity) == status]
    return entities


@entities_cli.command("list")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
@click.option('--type', 'entity_type',
              type=click.Choice(["adr", "system", "capability", "decision", "component", "invariant", "boundary", "contract", "constraint", "nfr", "gap", "interface", "integration", "implementation_decision"]),
              help='Filter by entity type')
@click.option('--adr', 'adr_id', help='Filter by ADR reference')
@click.option('--domain', help='Filter by domain')
@click.option('--status', type=click.Choice(["proposed", "active", "deprecated", "superseded"]),
              help='Filter by lifecycle stage')
def entities_list(scope: Optional[Path], entity_type: Optional[str], adr_id: Optional[str], domain: Optional[str], status: Optional[str]):
    """List entities from the generated registry."""
    try:
        repository = _load_architecture_repository(scope)
        entities = _filter_entities(
            repository.legacy_entity_registry or repository.primary_entity_registry,
            entity_type=entity_type,
            adr=adr_id,
            domain=domain,
            status=status,
        )
        click.echo(_dump_yaml({"entities": [entity.model_dump(mode="json", exclude_none=True) for entity in entities]}))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@entities_cli.command("get")
@click.argument("entity_id")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
def entities_get(entity_id: str, scope: Optional[Path]):
    """Get an entity by exact ID."""
    try:
        repository = _load_architecture_repository(scope)
        entity = repository.find_entity(entity_id)
        if entity is None:
            raise ValueError(f"Entity not found: {entity_id}")
        click.echo(_dump_yaml(entity.model_dump(mode="json", exclude_none=True)))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@entities_cli.command("invariants")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
@click.option('--adr', 'adr_id', help='Filter by ADR reference')
@click.option('--domain', help='Filter by domain')
@click.option('--status', type=click.Choice(["proposed", "active", "deprecated", "superseded"]),
              help='Filter by lifecycle stage')
def entities_invariants(scope: Optional[Path], adr_id: Optional[str], domain: Optional[str], status: Optional[str]):
    """List invariants from the generated registry."""
    try:
        repository = _load_architecture_repository(scope)
        entities = _filter_entities(
            type("RegistryView", (), {"entities": repository.get_invariants()})(),
            entity_type="invariant",
            adr=adr_id,
            domain=domain,
            status=status,
        )
        click.echo(_dump_yaml({"entities": [entity.model_dump(mode="json", exclude_none=True) for entity in entities]}))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@entities_cli.command("capabilities")
@click.option('--scope', type=click.Path(exists=True, file_okay=False, path_type=Path),
              help='Explicit project scope (overrides auto-detection)')
@click.option('--adr', 'adr_id', help='Filter by ADR reference')
@click.option('--domain', help='Filter by domain')
@click.option('--status', type=click.Choice(["proposed", "active", "deprecated", "superseded"]),
              help='Filter by lifecycle stage')
def entities_capabilities(scope: Optional[Path], adr_id: Optional[str], domain: Optional[str], status: Optional[str]):
    """List capabilities from the generated registry."""
    try:
        repository = _load_architecture_repository(scope)
        entities = _filter_entities(
            type("RegistryView", (), {"entities": repository.get_capabilities()})(),
            entity_type="capability",
            adr=adr_id,
            domain=domain,
            status=status,
        )
        click.echo(_dump_yaml({"entities": [entity.model_dump(mode="json", exclude_none=True) for entity in entities]}))
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
