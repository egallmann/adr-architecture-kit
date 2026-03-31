"""Test project scope resolver (ADR-P-0003: COMP-0001)."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil

from src.adr_kit.scope import ProjectScopeResolver, ProjectScope


class TestProjectScopeDetection:
    """Test automatic project scope detection (ADR-L-0002: CAP-0001)."""
    
    def test_explicit_scope_overrides_detection(self):
        """Test INV-0014: Explicit scope parameter overrides auto-detection."""
        explicit_path = Path("/explicit/project")
        resolver = ProjectScopeResolver(explicit_scope=explicit_path)
        
        scope = resolver.resolve(start_dir=Path("/different/location"))
        
        assert scope.root == explicit_path.resolve()
        assert scope.marker == 'explicit'
    
    def test_detect_from_project_yaml(self, tmp_path):
        """Test detection via PROJECT.yaml marker."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "PROJECT.yaml").write_text("project:\n  name: test")
        (project_dir / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=project_dir)
        
        assert scope.root == project_dir
        assert scope.marker == 'PROJECT.yaml'
        assert scope.adr_dir == project_dir / "adrs"
    
    def test_detect_from_ste_config(self, tmp_path):
        """Test detection via ste.config.json (authoritative marker)."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "ste.config.json").write_text('{"projectRoot": "."}')
        (project_dir / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=project_dir)
        
        assert scope.root == project_dir
        assert scope.marker == 'ste.config.json'
    
    def test_detect_from_package_json(self, tmp_path):
        """Test detection via package.json marker."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "package.json").write_text('{"name": "test"}')
        (project_dir / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=project_dir)
        
        assert scope.root == project_dir
        assert scope.marker == 'package.json'
    
    def test_detect_from_pyproject_toml(self, tmp_path):
        """Test detection via pyproject.toml marker."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (project_dir / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=project_dir)
        
        assert scope.root == project_dir
        assert scope.marker == 'pyproject.toml'
    
    def test_detect_from_subdirectory(self, tmp_path):
        """Test detection when starting from subdirectory."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "PROJECT.yaml").write_text("project:\n  name: test")
        
        subdir = project_dir / "src" / "module"
        subdir.mkdir(parents=True)
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=subdir)
        
        assert scope.root == project_dir
        assert scope.marker == 'PROJECT.yaml'
    
    def test_marker_priority_order(self, tmp_path):
        """Test INV-0015: Marker hierarchy priority."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        
        # Create multiple markers
        (project_dir / "ste.config.json").write_text('{}')
        (project_dir / "PROJECT.yaml").write_text('project:\n  name: test')
        (project_dir / "package.json").write_text('{"name": "test"}')
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=project_dir)
        
        # ste.config.json should win (highest priority)
        assert scope.marker == 'ste.config.json'
    
    def test_no_project_found_raises_error(self, tmp_path):
        """Test error when no project markers found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        resolver = ProjectScopeResolver()
        resolver.SYSTEM_BOUNDARIES = [*resolver.SYSTEM_BOUNDARIES, tmp_path.name]

        with pytest.raises(ValueError, match="Could not determine project root"):
            resolver.resolve(start_dir=empty_dir)


class TestWorkspaceBoundaries:
    """Test workspace boundary enforcement (ADR-L-0002: INV-0018)."""
    
    def test_stops_at_documents_directory(self):
        """Test INV-0018: Don't traverse above Documents."""
        # This is a safety test - we don't want to scan entire home directory
        resolver = ProjectScopeResolver()
        
        # Create a path that would traverse to Documents
        test_path = Path.home() / "Documents" / "test-project"
        
        # Should stop at Documents boundary
        assert resolver._is_workspace_boundary(Path.home() / "Documents")
    
    def test_stops_at_users_directory(self):
        """Test INV-0018: Don't traverse above Users."""
        resolver = ProjectScopeResolver()
        
        # On Windows: C:\Users
        users_path = Path("C:/Users")
        assert resolver._is_workspace_boundary(users_path)


class TestSubModuleDetection:
    """Test sub-module scope detection (ADR-L-0002: INV-0016)."""
    
    def test_detect_parent_scope(self, tmp_path):
        """Test detection of parent scope for sub-modules."""
        # Create workspace with sub-module
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "PROJECT.yaml").write_text("project:\n  name: workspace")
        (workspace / "adrs").mkdir()
        
        submodule = workspace / "sub-module"
        submodule.mkdir()
        (submodule / "package.json").write_text('{"name": "sub-module"}')
        (submodule / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=submodule)
        
        assert scope.root == submodule
        assert scope.is_sub_module is True
        assert scope.parent_scope is not None
        assert scope.parent_scope.root == workspace
    
    def test_workspace_root_not_sub_module(self, tmp_path):
        """Test workspace root is not marked as sub-module."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "PROJECT.yaml").write_text("project:\n  name: workspace")
        (workspace / "adrs").mkdir()

        resolver = ProjectScopeResolver()
        resolver.SYSTEM_BOUNDARIES = [*resolver.SYSTEM_BOUNDARIES, tmp_path.name]
        scope = resolver.resolve(start_dir=workspace)

        assert scope.is_sub_module is False
        assert scope.parent_scope is None


class TestRecursiveScopeDiscovery:
    """Test recursive scope discovery (ADR-L-0002: CAP-0001)."""
    
    def test_find_all_sub_modules(self, tmp_path):
        """Test recursive discovery finds all sub-modules."""
        # Create workspace with multiple sub-modules
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "PROJECT.yaml").write_text("project:\n  name: workspace")
        (workspace / "adrs").mkdir()
        
        # Sub-module 1
        sub1 = workspace / "module1"
        sub1.mkdir()
        (sub1 / "package.json").write_text('{"name": "module1"}')
        (sub1 / "adrs").mkdir()
        
        # Sub-module 2
        sub2 = workspace / "module2"
        sub2.mkdir()
        (sub2 / "pyproject.toml").write_text('[project]\nname = "module2"')
        (sub2 / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scopes = resolver.resolve_recursive(start_dir=workspace)
        
        assert len(scopes) == 3  # workspace + 2 sub-modules
        assert scopes[0].root == workspace
        assert any(s.root == sub1 for s in scopes)
        assert any(s.root == sub2 for s in scopes)
    
    def test_recursive_max_depth(self, tmp_path):
        """Test recursive search respects max depth (2 levels)."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "PROJECT.yaml").write_text("project:\n  name: workspace")
        
        # Deep nesting
        deep = workspace / "level1" / "level2" / "level3"
        deep.mkdir(parents=True)
        (deep / "package.json").write_text('{"name": "deep"}')
        
        resolver = ProjectScopeResolver()
        scopes = resolver.resolve_recursive(start_dir=workspace)
        
        # Should not find level3 (too deep)
        assert not any(s.root == deep for s in scopes)


class TestProjectScopeMetadata:
    """Test ProjectScope metadata extraction."""
    
    def test_extract_name_from_project_yaml(self, tmp_path):
        """Test project name extraction from PROJECT.yaml."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "PROJECT.yaml").write_text(
            "project:\n  name: my-awesome-project\n  description: test"
        )
        (project_dir / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=project_dir)
        
        assert scope.name == "my-awesome-project"
    
    def test_fallback_to_directory_name(self, tmp_path):
        """Test fallback to directory name when PROJECT.yaml missing."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / "package.json").write_text('{"name": "different-name"}')
        (project_dir / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=project_dir)
        
        # Should use directory name as fallback
        assert scope.name == "my-project"
    
    def test_scope_paths_are_absolute(self, tmp_path):
        """Test that scope paths are resolved to absolute paths."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()
        (project_dir / "PROJECT.yaml").write_text("project:\n  name: test")
        (project_dir / "adrs").mkdir()
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=project_dir)
        
        assert scope.root.is_absolute()
        assert scope.adr_dir.is_absolute()
        assert scope.manifest_path.is_absolute()


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    def test_adr_architecture_kit_workspace(self):
        """Test detection in actual adr-architecture-kit workspace."""
        # This test runs in the real workspace
        workspace_root = Path(__file__).parent.parent
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=workspace_root)
        
        # Should detect workspace root
        assert scope.root == workspace_root
        assert scope.adr_dir == workspace_root / "adrs"
        assert (scope.root / "PROJECT.yaml").exists()
    
    def test_ste_runtime_submodule(self):
        """Test detection in ste-runtime sub-module."""
        workspace_root = Path(__file__).parent.parent
        ste_runtime = workspace_root / "ste-runtime"
        
        if not ste_runtime.exists():
            pytest.skip("ste-runtime not found")
        
        resolver = ProjectScopeResolver()
        scope = resolver.resolve(start_dir=ste_runtime)
        
        # Should detect ste-runtime as its own scope
        assert scope.root == ste_runtime
        assert scope.adr_dir == ste_runtime / "adrs"
        assert scope.is_sub_module is True
        assert scope.parent_scope is not None
        assert scope.parent_scope.root == workspace_root
    
    def test_recursive_finds_both_scopes(self):
        """Test recursive discovery finds workspace + ste-runtime."""
        workspace_root = Path(__file__).parent.parent
        
        resolver = ProjectScopeResolver()
        scopes = resolver.resolve_recursive(start_dir=workspace_root)
        
        # Should find at least workspace root
        assert len(scopes) >= 1
        assert scopes[0].root == workspace_root
        
        # Should find ste-runtime if it exists
        ste_runtime = workspace_root / "ste-runtime"
        if ste_runtime.exists():
            assert any(s.root == ste_runtime for s in scopes)
