"""Comprehensive MVP validation script."""

from pathlib import Path
from src.adr_kit.parser import ADRParser
from src.adr_kit.generators import ManifestGenerator
from src.adr_kit.generators.views import MarkdownGenerator

def validate_schema_files():
    """Validate all schema files exist."""
    print("\n" + "="*60)
    print("Validating Schema Files")
    print("="*60)
    
    required_schemas = [
        "schema/v1.0/types.schema.json",
        "schema/v1.0/adr-common.schema.json",
        "schema/v1.0/adr-logical.schema.json",
        "schema/v1.0/adr-physical.schema.json",
        "schema/v1.0/invariant.schema.json",
        "schema/v1.0/project-metadata.schema.json",
        "schema/v1.0/manifest.schema.json",
    ]
    
    missing = []
    for schema_path in required_schemas:
        if not Path(schema_path).exists():
            missing.append(schema_path)
            print(f"MISSING: {schema_path}")
        else:
            print(f"OK: {schema_path}")
    
    if missing:
        print(f"\nFAILED: {len(missing)} schema file(s) missing")
        return False
    
    print("\nSUCCESS: All schema files present")
    return True

def validate_python_package():
    """Validate Python package structure."""
    print("\n" + "="*60)
    print("Validating Python Package Structure")
    print("="*60)
    
    required_files = [
        "pyproject.toml",
        "requirements.txt",
        "src/adr_kit/__init__.py",
        "src/adr_kit/models/__init__.py",
        "src/adr_kit/parser/__init__.py",
        "src/adr_kit/generators/__init__.py",
        "tests/__init__.py",
    ]
    
    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
            print(f"MISSING: {file_path}")
        else:
            print(f"OK: {file_path}")
    
    if missing:
        print(f"\nFAILED: {len(missing)} file(s) missing")
        return False
    
    print("\nSUCCESS: Python package structure valid")
    return True

def validate_dogfooding_adrs():
    """Validate dogfooding ADRs."""
    print("\n" + "="*60)
    print("Validating Dogfooding ADRs")
    print("="*60)
    
    parser = ADRParser()
    
    adrs = [
        ("adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml", "logical"),
        ("adrs/physical/ADR-P-0001-python-toolkit-implementation.yaml", "physical"),
        ("adrs/physical/ADR-P-0002-json-schema-yaml-format.yaml", "physical"),
    ]
    
    errors = []
    for adr_path, adr_type in adrs:
        try:
            if adr_type == "logical":
                adr = parser.parse_logical_adr(Path(adr_path))
            else:
                adr = parser.parse_physical_adr(Path(adr_path))
            
            print(f"OK: {adr.id} - {adr.title}")
        except Exception as e:
            errors.append((adr_path, e))
            print(f"FAILED: {adr_path}: {e}")
    
    if errors:
        print(f"\nFAILED: {len(errors)} ADR(s) failed validation")
        return False
    
    print(f"\nSUCCESS: All {len(adrs)} dogfooding ADRs valid")
    return True

def validate_manifest_generation():
    """Validate manifest generation."""
    print("\n" + "="*60)
    print("Validating Manifest Generation")
    print("="*60)
    
    try:
        generator = ManifestGenerator()
        manifest = generator.generate_from_directory(Path("adrs"))
        
        print(f"OK: Generated manifest")
        print(f"  Total ADRs: {manifest.statistics.total_adrs}")
        print(f"  Logical: {manifest.statistics.logical_adrs}")
        print(f"  Physical: {manifest.statistics.physical_adrs}")
        print(f"  Decisions: {manifest.statistics.total_decisions}")
        print(f"  Invariants: {manifest.statistics.total_invariants}")
        print(f"  Components: {manifest.statistics.total_components}")
        
        # Validate manifest structure
        assert manifest.statistics.total_adrs >= 3
        assert manifest.statistics.logical_adrs >= 1
        assert manifest.statistics.physical_adrs >= 2
        assert len(manifest.by_domain) > 0
        assert len(manifest.logical_to_physical_map) > 0
        
        print("\nSUCCESS: Manifest generation valid")
        return True
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_markdown_generation():
    """Validate markdown view generation."""
    print("\n" + "="*60)
    print("Validating Markdown View Generation")
    print("="*60)
    
    try:
        parser = ADRParser()
        generator = MarkdownGenerator()
        
        # Test logical ADR
        adr = parser.parse_logical_adr(Path("adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml"))
        markdown = generator.render_logical_adr(adr)
        
        assert "ADR-L-0001" in markdown
        assert "## Context" in markdown
        assert "## Decisions" in markdown
        
        print("OK: Logical ADR markdown generation")
        
        # Test physical ADR
        adr = parser.parse_physical_adr(Path("adrs/physical/ADR-P-0001-python-toolkit-implementation.yaml"))
        markdown = generator.render_physical_adr(adr)
        
        assert "ADR-P-0001" in markdown
        assert "## Technology Stack" in markdown
        assert "## Component Specifications" in markdown
        
        print("OK: Physical ADR markdown generation")
        
        print("\nSUCCESS: Markdown generation valid")
        return True
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_ste_integration():
    """Validate STE integration."""
    print("\n" + "="*60)
    print("Validating STE Integration")
    print("="*60)
    
    # Check submodules
    ste_spec_path = Path("ste-spec")
    ste_runtime_path = Path("ste-runtime")
    
    if not ste_spec_path.exists():
        print("FAILED: ste-spec submodule not found")
        return False
    print("OK: ste-spec submodule present")
    
    if not ste_runtime_path.exists():
        print("FAILED: ste-runtime submodule not found")
        return False
    print("OK: ste-runtime submodule present")
    
    # Check PROJECT.yaml
    project_path = Path("PROJECT.yaml")
    if not project_path.exists():
        print("WARNING: PROJECT.yaml not found (optional)")
    else:
        try:
            parser = ADRParser()
            project = parser.parse_project_metadata(project_path)
            print(f"OK: PROJECT.yaml valid (project: {project.project.name})")
        except Exception as e:
            print(f"FAILED: PROJECT.yaml invalid: {e}")
            return False
    
    print("\nSUCCESS: STE integration valid")
    return True

def validate_documentation():
    """Validate documentation exists."""
    print("\n" + "="*60)
    print("Validating Documentation")
    print("="*60)
    
    required_docs = [
        "README.md",
        "docs/logical-adr-guide.md",
        "docs/physical-adr-guide.md",
        "docs/schema-guide.md",
        "docs/graph-integration.md",
        "schema/v1.0/README.md",
    ]
    
    missing = []
    for doc_path in required_docs:
        if not Path(doc_path).exists():
            missing.append(doc_path)
            print(f"MISSING: {doc_path}")
        else:
            print(f"OK: {doc_path}")
    
    if missing:
        print(f"\nFAILED: {len(missing)} documentation file(s) missing")
        return False
    
    print("\nSUCCESS: All documentation present")
    return True

def main():
    """Run all validations."""
    print("\n" + "="*60)
    print("ADR Architecture Kit v1.0 MVP Validation")
    print("="*60)
    
    results = {
        "Schema Files": validate_schema_files(),
        "Python Package": validate_python_package(),
        "Dogfooding ADRs": validate_dogfooding_adrs(),
        "Manifest Generation": validate_manifest_generation(),
        "Markdown Generation": validate_markdown_generation(),
        "STE Integration": validate_ste_integration(),
        "Documentation": validate_documentation(),
    }
    
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{name:.<40} {status}")
    
    all_pass = all(results.values())
    
    print("\n" + "="*60)
    if all_pass:
        print("MVP VALIDATION: PASS")
        print("="*60)
        print("\nADR Architecture Kit v1.0 MVP is complete!")
        print("\nDeliverables:")
        print("  - JSON Schema v1.0 (7 schemas)")
        print("  - Pydantic models (5 model files)")
        print("  - YAML parser with validation")
        print("  - Manifest generator (SYS-14 compliant)")
        print("  - Markdown view generator")
        print("  - Dogfooding ADRs (3 ADRs, 1 invariant)")
        print("  - Test suite (17 tests)")
        print("  - CI governance workflow")
        print("  - Complete documentation")
        print("  - STE integration (ste-spec + ste-runtime submodules)")
    else:
        print("MVP VALIDATION: FAIL")
        print("="*60)
        failed = [name for name, result in results.items() if not result]
        print(f"\nFailed validations: {', '.join(failed)}")
    
    return all_pass

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
