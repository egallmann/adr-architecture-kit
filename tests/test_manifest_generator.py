"""Test manifest generator."""

import pytest
from pathlib import Path

from src.adr_kit.generators import ManifestGenerator


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
        assert "ADR-P-0001" in manifest.logical_to_physical_map["ADR-L-0001"]
    
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
