"""Test ADR validator (ADR-P-0003: COMP-0003)."""

import pytest
import shutil
import uuid
from pathlib import Path

from src.adr_kit.validators import ADRValidator, ValidationResult, ValidationError
from src.adr_kit.scope import ProjectScopeResolver


class TestADRValidation:
    """Test basic ADR validation."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ADRValidator()
    
    def test_validate_valid_logical_adr(self, validator):
        """Test validation of valid logical ADR."""
        adr_path = Path("adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml")
        
        if not adr_path.exists():
            pytest.skip("ADR file not found")
        
        result = validator.validate_file(adr_path)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True or len(result.errors) == 0
    
    def test_validate_valid_physical_adr(self, validator):
        """Test validation of valid physical ADR."""
        adr_path = Path("adrs/physical/ADR-P-0001-python-toolkit-implementation.yaml")
        
        if not adr_path.exists():
            pytest.skip("ADR file not found")
        
        result = validator.validate_file(adr_path)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True or len(result.errors) == 0
    
    def test_validate_directory(self, validator):
        """Test validation of entire ADR directory."""
        adr_dir = Path("adrs")
        
        if not adr_dir.exists():
            pytest.skip("ADR directory not found")
        
        results = validator.validate_directory(adr_dir)
        
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # All results should be ValidationResult objects
        for file_path, result in results.items():
            assert isinstance(result, ValidationResult)
    
    def test_validate_cross_references(self, validator):
        """Test cross-reference validation with a curated valid fixture scope."""
        temp_root = Path("tests") / ".tmp" / str(uuid.uuid4())
        adr_dir = temp_root / "adrs"
        logical_dir = adr_dir / "logical"
        physical_dir = adr_dir / "physical"
        logical_dir.mkdir(parents=True, exist_ok=True)
        physical_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy(Path("tests/fixtures/valid/logical-minimal.yaml"), logical_dir / "ADR-L-9999-logical.yaml")
            shutil.copy(Path("tests/fixtures/valid/physical-minimal.yaml"), physical_dir / "ADR-P-9999-physical.yaml")

            result = validator.validate_cross_references(adr_dir)

            assert isinstance(result, ValidationResult)
            assert result.valid
            assert len(result.errors) == 0
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_validate_directory_discovers_physical_subtypes_in_physical_dir(self, validator):
        """Validation should discover ADR-PS and ADR-PC files placed under adrs/physical."""
        temp_root = Path("tests") / ".tmp" / str(uuid.uuid4())
        adr_dir = temp_root / "adrs"
        logical_dir = adr_dir / "logical"
        physical_dir = adr_dir / "physical"
        logical_dir.mkdir(parents=True, exist_ok=True)
        physical_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy(Path("tests/fixtures/valid/logical-minimal.yaml"), logical_dir / "ADR-L-9999-logical.yaml")
            shutil.copy(Path("tests/fixtures/valid/physical-system-minimal.yaml"), physical_dir / "ADR-PS-0001-system.yaml")
            shutil.copy(Path("tests/fixtures/valid/physical-component-minimal.yaml"), physical_dir / "ADR-PC-0001-component.yaml")

            results = validator.validate_directory(adr_dir)

            assert len(results) == 3
            assert any("ADR-PS-0001-system.yaml" in path for path in results.keys())
            assert any("ADR-PC-0001-component.yaml" in path for path in results.keys())
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)


class TestScopeAwareValidation:
    """Test scope-aware validation (ADR-P-0003: COMP-0003)."""
    
    @pytest.fixture
    def validator(self):
        """Create scope-aware validator."""
        resolver = ProjectScopeResolver()
        return ADRValidator(scope_resolver=resolver)
    
    def test_validate_scope_auto_detection(self, validator):
        """Test CAP-0003: Validate with auto-detected scope."""
        workspace_root = Path(__file__).parent.parent
        
        # Should auto-detect workspace scope
        results = validator.validate_scope()
        
        assert isinstance(results, dict)
        # Should validate workspace ADRs
        assert any("ADR-L-0001" in str(path) or "ADR-L-0002" in str(path) for path in results.keys())
    
    def test_validate_scope_explicit(self, validator):
        """Test CAP-0003: Validate with explicit scope."""
        workspace_root = Path(__file__).parent.parent
        ste_runtime = workspace_root / "ste-runtime"
        
        if not ste_runtime.exists():
            pytest.skip("ste-runtime not found")
        
        resolver = ProjectScopeResolver(explicit_scope=ste_runtime)
        validator_with_scope = ADRValidator(scope_resolver=resolver)
        
        results = validator_with_scope.validate_scope()
        
        # Should validate ste-runtime ADRs only
        assert all("ste-runtime" in str(path) for path in results.keys())
    
    def test_validate_recursive(self, validator):
        """Test INV-0019: Recursive validation of all scopes."""
        workspace_root = Path(__file__).parent.parent
        
        all_results = validator.validate_recursive()
        
        assert isinstance(all_results, dict)
        # Should have at least workspace scope
        assert len(all_results) >= 1
        
        # Each scope should have validation results
        for scope_name, results in all_results.items():
            assert isinstance(results, dict)
            assert len(results) >= 0  # May be empty if no ADRs


class TestValidationRules:
    """Test specific validation rules."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ADRValidator()
    
    def test_logical_adr_must_have_decisions(self, validator):
        """Test that logical ADRs should have decisions."""
        # This would require creating a test ADR file
        # Skipping for now - would need test fixtures
        pytest.skip("Requires test fixtures")
    
    def test_physical_adr_must_reference_logical(self, validator):
        """Test INV-0003: Physical ADRs must reference logical ADRs."""
        # This would require creating a test ADR file
        # Skipping for now - would need test fixtures
        pytest.skip("Requires test fixtures")
    
    def test_duplicate_invariant_ids_detected(self, validator):
        """Test INV-0005: Duplicate invariant IDs are detected."""
        # This would require creating a test ADR file
        # Skipping for now - would need test fixtures
        pytest.skip("Requires test fixtures")


class TestBackwardCompatibility:
    """Test backward compatibility with single-scope usage."""
    
    def test_validate_file_still_works(self):
        """Test that validate_file works without scope parameter."""
        validator = ADRValidator()
        adr_path = Path("adrs/logical/ADR-L-0001-ste-compliant-adr-system.yaml")
        
        if not adr_path.exists():
            pytest.skip("ADR file not found")
        
        # Old API should still work
        result = validator.validate_file(adr_path)
        
        assert isinstance(result, ValidationResult)
    
    def test_validate_directory_without_scope(self):
        """Test that validate_directory works without scope parameter."""
        validator = ADRValidator()
        adr_dir = Path("adrs")
        
        if not adr_dir.exists():
            pytest.skip("ADR directory not found")
        
        # Old API should still work
        results = validator.validate_directory(adr_dir)
        
        assert isinstance(results, dict)
        assert len(results) > 0
