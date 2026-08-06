"""Test multi-scope manifest generation (ADR-P-0003: COMP-0002)."""

import pytest
import shutil
import uuid
from pathlib import Path

from adr_kit.generators import ManifestGenerator
from adr_kit.scope import ProjectScopeResolver


class TestScopeAwareGeneration:
    """Test scope-aware manifest generation (ADR-L-0002: CAP-0002)."""
    
    @pytest.fixture
    def generator(self):
        """Create scope-aware generator."""
        resolver = ProjectScopeResolver()
        return ManifestGenerator(scope_resolver=resolver)
    
    def test_generate_from_scope_auto_detection(self, generator):
        """Test CAP-0002: Generate manifest with auto-detected scope."""
        workspace_root = Path(__file__).parent.parent
        
        # Should auto-detect workspace scope
        manifest = generator.generate_from_scope()
        
        assert manifest.schema_version == "1.0"
        assert manifest.type == "manifest"
        assert manifest.statistics.total_adrs >= 2  # At least ADR-L-0001, ADR-L-0002
    
    def test_generate_from_scope_explicit(self, generator):
        """Test CAP-0002: Generate manifest with explicit scope."""
        workspace_root = Path(__file__).parent.parent
        ste_runtime = workspace_root / "ste-runtime"
        
        if not ste_runtime.exists() or not (ste_runtime / "adrs").exists():
            pytest.skip("ste-runtime not found")
        
        resolver = ProjectScopeResolver(explicit_scope=ste_runtime)
        generator_with_scope = ManifestGenerator(scope_resolver=resolver)
        
        manifest = generator_with_scope.generate_from_scope()
        
        # Should generate ste-runtime manifest
        assert manifest.statistics.total_adrs >= 6  # ste-runtime has many ADRs
        # All file paths should be relative to ste-runtime
        assert all("adrs" in entry.file_path for entry in manifest.adrs)
    
    def test_generate_recursive(self, generator):
        """Test CAP-0002: Generate manifests for all scopes."""
        workspace_root = Path(__file__).parent.parent
        
        manifests = generator.generate_recursive()
        
        assert isinstance(manifests, dict)
        # Should have at least workspace scope
        assert len(manifests) >= 1
        
        # Each manifest should be valid
        for scope_name, manifest in manifests.items():
            assert manifest.schema_version == "1.0"
            assert manifest.type == "manifest"
            assert manifest.statistics.total_adrs >= 0
    
    def test_scoped_manifest_only_includes_scope_adrs(self, generator):
        """Test INV-0016: Manifest only includes ADRs from that scope."""
        workspace_root = Path(__file__).parent.parent
        
        # Generate workspace manifest
        workspace_resolver = ProjectScopeResolver(explicit_scope=workspace_root)
        workspace_generator = ManifestGenerator(scope_resolver=workspace_resolver)
        workspace_manifest = workspace_generator.generate_from_scope()
        
        # Should not include ste-runtime ADRs
        workspace_adr_ids = [adr.id for adr in workspace_manifest.adrs]
        
        # Generate ste-runtime manifest if it exists
        ste_runtime = workspace_root / "ste-runtime"
        if ste_runtime.exists() and (ste_runtime / "adrs").exists():
            ste_resolver = ProjectScopeResolver(explicit_scope=ste_runtime)
            ste_generator = ManifestGenerator(scope_resolver=ste_resolver)
            ste_manifest = ste_generator.generate_from_scope()
            
            ste_adr_ids = [adr.id for adr in ste_manifest.adrs]
            
            # No overlap - each scope has independent numbering
            # (They might have same IDs like ADR-L-0001, but different file paths)
            workspace_paths = [adr.file_path for adr in workspace_manifest.adrs]
            ste_paths = [adr.file_path for adr in ste_manifest.adrs]
            
            # Workspace paths should not include ste-runtime
            assert not any("ste-runtime" in path for path in workspace_paths)
            # ste-runtime paths should include ste-runtime or be relative
            assert all("adrs" in path for path in ste_paths)


class TestBackwardCompatibility:
    """Test backward compatibility with single-scope usage."""
    
    def test_generate_from_directory_still_works(self):
        """Test that generate_from_directory works without scope parameter."""
        generator = ManifestGenerator()
        adr_dir = Path("adrs")
        
        if not adr_dir.exists():
            pytest.skip("ADR directory not found")
        
        # Old API should still work
        manifest = generator.generate_from_directory(adr_dir)
        
        assert manifest.schema_version == "1.0"
        assert manifest.type == "manifest"
    
    def test_save_manifest_still_works(self):
        """Test that save_manifest works as before."""
        generator = ManifestGenerator()
        adr_dir = Path("adrs")
        
        if not adr_dir.exists():
            pytest.skip("ADR directory not found")
        
        temp_root = Path("tests") / ".tmp" / str(uuid.uuid4())
        output_path = temp_root / "test-manifest.yaml"

        try:
            manifest = generator.generate_from_directory(adr_dir)
            generator.save_manifest(manifest, output_path)

            assert output_path.exists()
            assert output_path.stat().st_size > 0
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_generate_from_nonexistent_directory(self):
        """Test error handling for non-existent ADR directory."""
        generator = ManifestGenerator()
        
        with pytest.raises(ValueError, match="ADR directory not found"):
            generator.generate_from_directory(Path("/nonexistent/adrs"))
    
    def test_generate_from_empty_directory(self):
        """Test generation from empty ADR directory."""
        temp_root = Path("tests") / ".tmp" / str(uuid.uuid4())
        empty_adrs = temp_root / "adrs"
        empty_adrs.mkdir(parents=True, exist_ok=True)
        (empty_adrs / "logical").mkdir()
        (empty_adrs / "physical").mkdir()

        try:
            generator = ManifestGenerator()
            manifest = generator.generate_from_directory(empty_adrs)

            assert manifest.statistics.total_adrs == 0
            assert manifest.statistics.logical_adrs == 0
            assert manifest.statistics.physical_adrs == 0
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)
