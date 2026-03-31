#!/usr/bin/env python3
"""CLI tool to migrate ste-runtime E-ADRs to ADR Kit format.

This script:
1. Parses E-ADR markdown files
2. Classifies as Logical or Physical
3. Generates YAML ADRs with reverse-engineered implementation details
4. Validates against JSON Schema
5. Generates manifest.yaml
6. Generates markdown views
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from adr_kit.migrators import MarkdownToYAMLMigrator
from adr_kit.generators.manifest_generator import ManifestGenerator
from adr_kit.generators.views.markdown import MarkdownGenerator
from adr_kit.validators import ADRValidator


def main():
    """Run E-ADR migration."""
    parser = argparse.ArgumentParser(
        description="Migrate ste-runtime E-ADRs to ADR Kit YAML format"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Input directory containing E-ADR markdown files (e.g., ste-runtime/documentation/e-adr/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for migrated ADRs (e.g., ste-runtime/adrs/)",
    )
    parser.add_argument(
        "--ste-runtime-root",
        type=Path,
        required=True,
        help="Path to ste-runtime project root (for reverse-engineering)",
    )
    parser.add_argument(
        "--generate-manifest",
        action="store_true",
        default=True,
        help="Generate manifest.yaml after migration (default: True)",
    )
    parser.add_argument(
        "--generate-views",
        action="store_true",
        default=True,
        help="Generate markdown views after migration (default: True)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate migrated ADRs (default: True)",
    )
    
    args = parser.parse_args()
    
    # Validate paths
    if not args.input_dir.exists():
        print(f"Error: Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    if not args.ste_runtime_root.exists():
        print(f"Error: ste-runtime root not found: {args.ste_runtime_root}")
        sys.exit(1)
    
    # Initialize migrator
    print(f"Initializing migrator...")
    migrator = MarkdownToYAMLMigrator(ste_runtime_root=args.ste_runtime_root)
    
    # Find all E-ADR files
    eadr_files = sorted(args.input_dir.glob("E-ADR-*.md"))
    print(f"Found {len(eadr_files)} E-ADR files")
    
    # Migrate each E-ADR
    migrated_count = 0
    skipped_count = 0
    failed_count = 0
    
    for eadr_file in eadr_files:
        print(f"\nMigrating {eadr_file.name}...")
        
        try:
            result = migrator.migrate_eadr(eadr_file)
            
            if result is None:
                print(f"  -> Skipped (documentation guide)")
                skipped_count += 1
                continue
            
            # Save migrated ADR
            output_path = migrator.save_migrated_adr(result, args.output_dir)
            print(f"  -> Saved to {output_path}")
            migrated_count += 1
            
        except Exception as e:
            print(f"  -> Failed: {e}")
            failed_count += 1
    
    print(f"\n{'='*60}")
    print(f"Migration Summary:")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped:  {skipped_count}")
    print(f"  Failed:   {failed_count}")
    print(f"{'='*60}")
    
    if failed_count > 0:
        print(f"\nWarning: {failed_count} E-ADRs failed to migrate")
    
    # Validate migrated ADRs
    if args.validate and migrated_count > 0:
        print(f"\nValidating migrated ADRs...")
        validator = ADRValidator(project_root=args.ste_runtime_root)
        
        validation_results = validator.validate_directory(args.output_dir)
        
        error_count = sum(1 for result in validation_results.values() if result.has_errors)
        warning_count = sum(1 for result in validation_results.values() if result.has_warnings)
        
        print(f"  Validation complete:")
        print(f"    Errors:   {error_count}")
        print(f"    Warnings: {warning_count}")
        
        if error_count > 0:
            print(f"\n  Validation errors found:")
            for file_path, result in validation_results.items():
                if result.has_errors:
                    print(f"    {Path(file_path).name}:")
                    for error in result.errors:
                        print(f"      - [{error.rule}] {error.message}")
        
        # Cross-reference validation
        print(f"\n  Validating cross-references...")
        cross_ref_result = validator.validate_cross_references(args.output_dir)
        
        if cross_ref_result.has_errors:
            print(f"    Cross-reference errors:")
            for error in cross_ref_result.errors:
                print(f"      - [{error.rule}] {error.message}")
        else:
            print(f"    [OK] All cross-references valid")
    
    # Generate manifest
    if args.generate_manifest and migrated_count > 0:
        print(f"\nGenerating manifest.yaml...")
        manifest_gen = ManifestGenerator()
        
        try:
            manifest = manifest_gen.generate_from_directory(args.output_dir)
            manifest_path = args.output_dir / "manifest.yaml"
            manifest_gen.save_manifest(manifest, manifest_path)
            
            print(f"  -> Saved to {manifest_path}")
            print(f"  Statistics:")
            print(f"    Total ADRs:     {manifest.statistics.total_adrs}")
            print(f"    Logical ADRs:   {manifest.statistics.logical_adrs}")
            print(f"    Physical ADRs:  {manifest.statistics.physical_adrs}")
            print(f"    Invariants:     {manifest.statistics.total_invariants}")
            
        except Exception as e:
            print(f"  -> Failed to generate manifest: {e}")
    
    # Generate markdown views
    if args.generate_views and migrated_count > 0:
        print(f"\nGenerating markdown views...")
        markdown_gen = MarkdownGenerator()
        
        rendered_dir = args.output_dir / "rendered"
        rendered_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse and render all ADRs
        from adr_kit.parser import ADRParser
        parser = ADRParser()
        
        logical_files = list((args.output_dir / "logical").glob("*.yaml"))
        physical_files = list((args.output_dir / "physical").glob("*.yaml"))
        
        rendered_count = 0
        for file_path in logical_files + physical_files:
            try:
                adr = parser.parse_adr(file_path)
                output_path = rendered_dir / f"{adr.id}.md"
                markdown_gen.render_to_file(adr, output_path)
                rendered_count += 1
            except Exception as e:
                print(f"  -> Failed to render {file_path.name}: {e}")
        
        print(f"  -> Rendered {rendered_count} markdown views to {rendered_dir}")
    
    print(f"\n[SUCCESS] Migration complete!")
    
    if migrated_count > 0:
        print(f"\nNext steps:")
        print(f"  1. Review migrated ADRs in {args.output_dir}")
        print(f"  2. Manually enrich: domains, tags, relationships")
        print(f"  3. Run RECON on migrated ADRs to validate graph extraction")
        print(f"  4. Archive original E-ADRs to documentation/e-adr-archived/")


if __name__ == "__main__":
    main()
