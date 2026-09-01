"""Test manifest generator."""

import pytest
import shutil
import uuid
from pathlib import Path

from adr_kit.generators import ManifestGenerator


@pytest.fixture
def generator():
    """Create manifest generator."""
    return ManifestGenerator()


class TestManifestGeneration:
    """Test manifest generation."""
    
    def test_generate_from_adrs_directory(self, generator):
        """Test generating manifest from adrs/ directory."""
        manifest = generator.generate_from_directory(Path("adrs"))
        
        assert manifest.schema_version == "1.0"
        assert manifest.type == "manifest"
        assert manifest.statistics.total_adrs >= 2
        assert manifest.statistics.logical_adrs >= 1
        assert manifest.statistics.physical_adrs >= 1
    
    def test_manifest_has_discovery_indexes(self, generator):
        """Test manifest includes discovery indexes."""
        manifest = generator.generate_from_directory(Path("adrs"))
        
        assert "architecture" in manifest.by_domain
        assert "accepted" in manifest.by_status
        assert len(manifest.by_technology) > 0
    
    def test_manifest_has_logical_to_physical_map(self, generator):
        """Test manifest includes logical to physical mapping."""
        manifest = generator.generate_from_directory(Path("adrs"))
        
        assert "ADR-L-0001" in manifest.logical_to_physical_map
        assert "ADR-PS-0002" in manifest.logical_to_physical_map["ADR-L-0001"]
    
    def test_manifest_statistics(self, generator):
        """Test manifest statistics are computed correctly."""
        manifest = generator.generate_from_directory(Path("adrs"))
        
        assert manifest.statistics.total_adrs == manifest.statistics.logical_adrs + manifest.statistics.physical_adrs
        assert manifest.statistics.total_decisions >= 6
        assert manifest.statistics.total_invariants >= 7
        assert manifest.statistics.total_components >= 4
    
    def test_manifest_gaps_summary(self, generator):
        """Test manifest gaps summary."""
        manifest = generator.generate_from_directory(Path("adrs"))
        
        assert manifest.gaps_summary.total >= 0
        assert manifest.gaps_summary.blocking >= 0
        assert manifest.gaps_summary.blocking <= manifest.gaps_summary.total

    def test_manifest_classifies_physical_subtypes_from_frontmatter_in_physical_dir(self):
        """Physical ADR subtypes should be discovered from frontmatter, not subfolders."""
        temp_root = Path("tests") / ".tmp" / str(uuid.uuid4())
        adr_dir = temp_root / "adrs"
        logical_dir = adr_dir / "logical"
        physical_dir = adr_dir / "physical"
        logical_dir.mkdir(parents=True, exist_ok=True)
        physical_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy(Path("tests/fixtures/valid/logical-minimal.yaml"), logical_dir / "ADR-L-9999-logical.yaml")
            shutil.copy(Path("tests/fixtures/valid/physical-minimal.yaml"), physical_dir / "ADR-P-9999-physical.yaml")
            shutil.copy(Path("tests/fixtures/valid/physical-system-minimal.yaml"), physical_dir / "ADR-PS-0001-system.yaml")
            shutil.copy(Path("tests/fixtures/valid/physical-component-minimal.yaml"), physical_dir / "ADR-PC-0001-component.yaml")

            manifest = ManifestGenerator().generate_from_directory(adr_dir)

            assert manifest.statistics.logical_adrs == 1
            assert manifest.statistics.physical_adrs == 3
            assert manifest.statistics.physical_system_adrs == 1
            assert manifest.statistics.physical_component_adrs == 1
            assert any(entry.type == "physical-system" for entry in manifest.adrs)
            assert any(entry.type == "physical-component" for entry in manifest.adrs)
            assert any(entry.file_path.endswith("adrs/physical/ADR-PS-0001-system.yaml") for entry in manifest.adrs)
            assert all("\\" not in entry.file_path for entry in manifest.adrs)
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)
