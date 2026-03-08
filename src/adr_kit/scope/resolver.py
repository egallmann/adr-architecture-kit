"""Project scope resolver - detects project boundaries for ADR operations.

Implements INV-0015: Project scope resolution using marker hierarchy.
Mirrors ste-runtime's scope detection pattern for consistency.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


@dataclass
class ProjectScope:
    """Resolved project scope information."""
    
    root: Path
    """Absolute path to project root directory"""
    
    adr_dir: Path
    """Absolute path to ADRs directory (root/adrs)"""
    
    manifest_path: Path
    """Absolute path to manifest.yaml"""
    
    marker: str
    """Marker file/directory that identified this scope"""
    
    name: Optional[str] = None
    """Project name (from PROJECT.yaml or package metadata)"""
    
    is_sub_module: bool = False
    """True if this is a sub-module within a larger workspace"""
    
    parent_scope: Optional['ProjectScope'] = None
    """Parent project scope if this is a sub-module"""


class ProjectScopeResolver:
    """Resolve project scope for ADR operations.
    
    Implements INV-0015 marker hierarchy:
    1. Explicit scope parameter (highest priority)
    2. ste.config.json in current or parent directories
    3. PROJECT.yaml (ADR-specific marker)
    4. Standard project markers (package.json, pyproject.toml, .git)
    5. Current working directory (fallback)
    """
    
    # Marker files in priority order
    MARKERS = [
        'ste.config.json',     # STE configuration (authoritative)
        'PROJECT.yaml',         # ADR project metadata
        'pyproject.toml',      # Python project
        'package.json',        # Node.js project
        'Cargo.toml',          # Rust project
        'go.mod',              # Go project
        '.git',                # Git repository root
    ]
    
    # System directories to never traverse above (INV-0018)
    SYSTEM_BOUNDARIES = [
        'Users',
        'home',
        'Documents',
    ]
    
    def __init__(self, explicit_scope: Optional[Path] = None):
        """Initialize resolver.
        
        Args:
            explicit_scope: Explicit project root (overrides auto-detection)
        """
        self.explicit_scope = Path(explicit_scope).resolve() if explicit_scope else None
    
    def resolve(self, start_dir: Optional[Path] = None) -> ProjectScope:
        """Resolve project scope starting from directory.
        
        Args:
            start_dir: Directory to start search from (default: cwd)
            
        Returns:
            Resolved ProjectScope
            
        Raises:
            ValueError: If no project root can be determined
        """
        # Priority 1: Explicit scope parameter (INV-0015)
        if self.explicit_scope:
            return self._create_scope(self.explicit_scope, 'explicit')
        
        # Start from current directory if not specified
        current = Path(start_dir).resolve() if start_dir else Path.cwd()
        
        # Priority 2-4: Search for markers (INV-0015)
        project_root = self._find_project_root(current)
        
        if not project_root:
            raise ValueError(
                f"Could not determine project root from {current}. "
                f"No markers found: {', '.join(self.MARKERS)}"
            )
        
        # Check if this is a sub-module by looking for parent project
        parent_scope = self._find_parent_scope(project_root)
        
        scope = self._create_scope(project_root, 'auto-detected')
        scope.is_sub_module = parent_scope is not None
        scope.parent_scope = parent_scope
        
        return scope
    
    def resolve_recursive(self, start_dir: Optional[Path] = None) -> List[ProjectScope]:
        """Resolve all project scopes recursively (workspace + sub-modules).
        
        Args:
            start_dir: Directory to start search from (default: cwd)
            
        Returns:
            List of ProjectScope objects (parent first, then children)
        """
        scopes = []
        
        # Get root scope
        root_scope = self.resolve(start_dir)
        scopes.append(root_scope)
        
        # Find all sub-module scopes
        sub_scopes = self._find_sub_modules(root_scope.root)
        scopes.extend(sub_scopes)
        
        return scopes
    
    def _find_project_root(self, start_dir: Path) -> Optional[Path]:
        """Find project root by searching for markers.
        
        Implements INV-0018: Stop at workspace boundary.
        """
        current = start_dir
        root = Path(current.anchor)  # Drive root on Windows, / on Unix
        
        while current != root:
            # Check for workspace boundary (INV-0018)
            if self._is_workspace_boundary(current):
                # Found boundary, check if current dir has markers
                for marker in self.MARKERS:
                    if (current / marker).exists():
                        return current
                # No markers at boundary, stop here
                return None
            
            # Check for markers in current directory
            for marker in self.MARKERS:
                marker_path = current / marker
                if marker_path.exists():
                    return current
            
            # Move up one level
            parent = current.parent
            if parent == current:
                break
            current = parent
        
        return None
    
    def _is_workspace_boundary(self, path: Path) -> bool:
        """Check if path is a workspace boundary (INV-0018).
        
        Stop traversal at system directories to prevent scanning
        unintended locations like home directory.
        """
        path_parts = path.parts
        
        # Check if any part matches system boundaries
        for boundary in self.SYSTEM_BOUNDARIES:
            if boundary in path_parts:
                # Check if we're AT the boundary (not below it)
                if path.name == boundary:
                    return True
        
        return False
    
    def _find_parent_scope(self, project_root: Path) -> Optional[ProjectScope]:
        """Find parent project scope if this is a sub-module.
        
        Args:
            project_root: Current project root
            
        Returns:
            Parent ProjectScope or None if this is top-level
        """
        parent_dir = project_root.parent
        
        # Try to find parent project markers
        parent_root = self._find_project_root(parent_dir)
        
        if parent_root and parent_root != project_root:
            return self._create_scope(parent_root, 'parent')
        
        return None
    
    def _find_sub_modules(self, root: Path) -> List[ProjectScope]:
        """Find all sub-module projects within root.
        
        Args:
            root: Root directory to search
            
        Returns:
            List of sub-module ProjectScope objects
        """
        sub_scopes = []
        
        # Search for markers in subdirectories (max 2 levels deep)
        for depth in range(1, 3):
            pattern = '/'.join(['*'] * depth)
            for marker in self.MARKERS:
                for marker_path in root.glob(f"{pattern}/{marker}"):
                    sub_root = marker_path.parent
                    
                    # Skip if this is the root itself
                    if sub_root == root:
                        continue
                    
                    # Skip if already found via different marker
                    if any(scope.root == sub_root for scope in sub_scopes):
                        continue
                    
                    # Create scope for sub-module
                    scope = self._create_scope(sub_root, marker)
                    scope.is_sub_module = True
                    sub_scopes.append(scope)
        
        return sub_scopes
    
    def _create_scope(self, root: Path, marker: str) -> ProjectScope:
        """Create ProjectScope from root directory.
        
        Args:
            root: Project root directory
            marker: Marker that identified this scope
            
        Returns:
            ProjectScope object
        """
        root = root.resolve()
        adr_dir = root / 'adrs'
        manifest_path = adr_dir / 'manifest.yaml'
        
        # Try to get project name from PROJECT.yaml
        name = None
        project_yaml = root / 'PROJECT.yaml'
        if project_yaml.exists():
            try:
                import yaml
                with open(project_yaml, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'project' in data:
                        name = data['project'].get('name')
            except Exception:
                pass
        
        # Fallback to directory name
        if not name:
            name = root.name
        
        return ProjectScope(
            root=root,
            adr_dir=adr_dir,
            manifest_path=manifest_path,
            marker=marker,
            name=name,
        )
