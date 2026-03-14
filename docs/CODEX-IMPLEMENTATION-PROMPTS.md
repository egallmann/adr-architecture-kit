# CODEX Implementation Prompts - Multi-Scope ADR Architecture

**Generated**: 2026-03-08  
**Authority**: ADR-L-0002, ADR-P-0003  
**Purpose**: Guide CODEX implementation with well-defined constraints

---

## Overview

These prompts guide CODEX to implement the multi-scope ADR architecture defined in:
- **ADR-L-0002**: Multi-Scope ADR Architecture (Logical)
- **ADR-P-0003**: Multi-Scope Python Implementation (Physical)

Each prompt includes:
- **Constraints**: What MUST be enforced (from invariants)
- **Specifications**: What to build (from component specs)
- **Test Requirements**: What to verify (from testing requirements)
- **Validation**: How I'll verify correctness

---

## Prompt 1: Implement Project Scope Resolver (COMP-0001)

### Context
You are implementing the Project Scope Resolver for the ADR Architecture Kit. This module detects project boundaries in a monorepo by searching for marker files.

### Constraints (MUST enforce)

**INV-0015**: Use this exact marker hierarchy (highest to lowest priority):
1. Explicit `--scope` parameter (if provided)
2. `ste.config.json` in current or parent directories
3. `PROJECT.yaml` in current or parent directories
4. `pyproject.toml` (Python projects)
5. `package.json` (Node projects)
6. `.git` directory (repository root)

**INV-0018**: MUST NOT traverse above workspace root. Stop at:
- First `.git` directory found
- System boundaries: `Users`, `Documents`, `home`, `/`

**INV-0014**: MUST support explicit scope override parameter

### Component Specification (COMP-0001)

**File**: `src/adr_kit/scope/resolver.py`

**Dataclass**: `ProjectScope`
```python
@dataclass(frozen=True)
class ProjectScope:
    root: Path              # Project root directory
    adr_dir: Path           # ADRs directory (root/adrs)
    manifest_path: Path     # Manifest file (root/adrs/manifest.yaml)
    marker: str             # Detection marker used
    name: Optional[str]     # Project name (from PROJECT.yaml or None)
    is_sub_module: bool     # True if parent scope exists
    parent_scope: Optional['ProjectScope']  # Parent scope reference
```

**Class**: `ProjectScopeResolver`

**Methods**:
1. `resolve(start_dir: Path = None) -> ProjectScope`
   - Auto-detect single scope from start_dir (defaults to cwd)
   - Return ProjectScope with detected metadata
   - Raise clear error if no project found

2. `resolve_recursive(start_dir: Path = None) -> List[ProjectScope]`
   - Find workspace root scope
   - Discover all sub-module scopes
   - Return list of all scopes (workspace + sub-modules)

**Private Methods** (suggested):
- `_find_project_root(start_dir: Path) -> Tuple[Path, str]`
  - Search for markers using hierarchy
  - Return (root_path, marker_name)
  
- `_is_workspace_boundary(path: Path) -> bool`
  - Check if path is workspace root (.git exists)
  - Check if path is system boundary
  
- `_find_parent_scope(scope: ProjectScope) -> Optional[ProjectScope]`
  - Search parent directories for another scope
  
- `_find_sub_modules(scope: ProjectScope) -> List[ProjectScope]`
  - Scan subdirectories for additional scopes
  - Don't recurse into already-detected scopes

### Test Requirements

**File**: `tests/test_scope_resolver.py`

Required tests:
1. `test_explicit_scope_overrides_detection` - INV-0014
2. `test_detect_from_ste_config` - Marker priority
3. `test_detect_from_project_yaml` - Marker priority
4. `test_detect_from_pyproject_toml` - Marker priority
5. `test_marker_priority_order` - INV-0015 hierarchy
6. `test_stops_at_git_directory` - INV-0018 boundary
7. `test_stops_at_documents_directory` - INV-0018 system boundary
8. `test_detect_parent_scope` - Parent-child relationships
9. `test_find_all_sub_modules` - Recursive discovery
10. `test_adr_architecture_kit_workspace` - Real workspace test

### Implementation Strategy (IMPL-0001: TDD)

**Red-Green-Refactor Cycle**:
1. **Red**: Write failing test for marker detection
2. **Green**: Implement `_find_project_root()` to pass
3. **Refactor**: Extract boundary checking
4. **Red**: Write failing test for boundary enforcement
5. **Green**: Implement `_is_workspace_boundary()`
6. **Refactor**: Clean up path handling
7. Continue for all methods...

### Dependencies
```python
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple
import yaml  # For PROJECT.yaml parsing
```

### Validation Criteria

I will verify:
- ✅ All 10 tests pass
- ✅ Marker hierarchy matches INV-0015 exactly
- ✅ Workspace boundary enforcement (INV-0018)
- ✅ Real workspace detection works (adr-architecture-kit + ste-runtime)
- ✅ Clear error messages when no project found
- ✅ Type hints are correct and complete

---

## Prompt 2: Enhance Manifest Generator (COMP-0002)

### Context
You are enhancing the existing `ManifestGenerator` class to support multi-scope operations while maintaining backward compatibility.

### Constraints (MUST enforce)

**INV-0016**: Each scope MUST maintain its own `adrs/` directory and `manifest.yaml`

**IMPL-0004**: Existing single-scope code MUST continue working without changes (backward compatibility)

### Component Specification (COMP-0002)

**File**: `src/adr_kit/generators/manifest_generator.py` (modify existing)

**Changes to `__init__`**:
```python
def __init__(
    self, 
    parser: Optional[ADRParser] = None,
    scope_resolver: Optional[ProjectScopeResolver] = None
):
    self.parser = parser or ADRParser()
    self.scope_resolver = scope_resolver or ProjectScopeResolver()
```

**Modify existing method**:
```python
def generate_from_directory(
    self, 
    adr_dir: Path,
    scope: Optional[ProjectScope] = None
) -> Manifest:
    """
    Generate manifest from ADR directory.
    
    If scope is provided, use it. Otherwise, auto-detect from adr_dir.
    This maintains backward compatibility while enabling scope awareness.
    """
    # Implementation...
```

**New methods**:
```python
def generate_from_scope(
    self,
    scope: Optional[ProjectScope] = None
) -> Manifest:
    """
    Generate manifest for a specific scope.
    
    If scope is None, auto-detect from current directory.
    """
    # Implementation...

def generate_recursive(
    self,
    scope: Optional[ProjectScope] = None
) -> Dict[str, Manifest]:
    """
    Generate manifests for workspace and all sub-modules.
    
    Returns dict mapping scope name to Manifest.
    """
    # Implementation...
```

### Test Requirements

**File**: `tests/test_multi_scope_generator.py`

Required tests:
1. `test_generate_from_scope_auto_detection` - Auto-detect works
2. `test_generate_from_scope_explicit` - Explicit scope works
3. `test_generate_recursive` - Finds all scopes
4. `test_scoped_manifest_only_includes_scope_adrs` - INV-0016 isolation
5. `test_generate_from_directory_still_works` - IMPL-0004 backward compat

### Implementation Strategy (IMPL-0001: TDD)

**Red-Green-Refactor**:
1. **Red**: Test auto-detection in `generate_from_scope()`
2. **Green**: Add scope resolution logic
3. **Refactor**: Extract common logic
4. **Red**: Test recursive generation
5. **Green**: Implement `generate_recursive()`
6. **Refactor**: Ensure backward compatibility

### Dependencies
```python
from adr_kit.scope import ProjectScopeResolver, ProjectScope
from typing import Optional, Dict
```

### Validation Criteria

I will verify:
- ✅ All 5 tests pass
- ✅ Backward compatibility: Old code works unchanged
- ✅ Scope isolation: Manifest only includes ADRs from its scope
- ✅ Recursive generation finds all scopes
- ✅ No breaking changes to existing API

---

## Prompt 3: Enhance ADR Validator (COMP-0003)

### Context
You are enhancing the existing `ADRValidator` class to support multi-scope validation while maintaining backward compatibility.

### Constraints (MUST enforce)

**INV-0019**: Recursive validation SHOULD validate all sub-module ADRs when `--recursive` flag is provided

**IMPL-0004**: Existing single-scope code MUST continue working without changes

### Component Specification (COMP-0003)

**File**: `src/adr_kit/validators/adr_validator.py` (modify existing)

**Changes to `__init__`**:
```python
def __init__(
    self,
    parser: Optional[ADRParser] = None,
    project_root: Optional[Path] = None,
    scope_resolver: Optional[ProjectScopeResolver] = None
):
    self.parser = parser or ADRParser()
    self.project_root = project_root
    self.scope_resolver = scope_resolver or ProjectScopeResolver()
```

**Modify existing method**:
```python
def validate_directory(
    self,
    adr_dir: Path,
    scope: Optional[ProjectScope] = None
) -> dict:
    """
    Validate ADRs in directory.
    
    If scope is provided, use it. Otherwise, auto-detect.
    Maintains backward compatibility.
    """
    # Implementation...
```

**New methods**:
```python
def validate_scope(
    self,
    scope: Optional[ProjectScope] = None
) -> dict:
    """
    Validate ADRs in a specific scope.
    
    If scope is None, auto-detect from current directory.
    """
    # Implementation...

def validate_recursive(
    self,
    scope: Optional[ProjectScope] = None
) -> Dict[str, dict]:
    """
    Validate ADRs in workspace and all sub-modules.
    
    Returns dict mapping scope name to validation results.
    """
    # Implementation...
```

### Test Requirements

**File**: `tests/test_adr_validator.py` (create if doesn't exist)

Required tests:
1. `test_validate_valid_logical_adr` - Basic validation works
2. `test_validate_directory` - Directory validation works
3. `test_validate_cross_references` - Cross-ref validation
4. `test_validate_scope_auto_detection` - Auto-detect works
5. `test_validate_recursive` - INV-0019 recursive validation
6. `test_validate_file_still_works` - Backward compatibility

### Implementation Strategy (IMPL-0001: TDD)

**Red-Green-Refactor**:
1. **Red**: Test basic validator functionality (if missing)
2. **Green**: Ensure existing validation works
3. **Red**: Test scope-aware validation
4. **Green**: Add scope resolution
5. **Red**: Test recursive validation
6. **Green**: Implement recursive logic
7. **Refactor**: Ensure backward compatibility

### Dependencies
```python
from adr_kit.scope import ProjectScopeResolver, ProjectScope
from typing import Optional, Dict
```

### Validation Criteria

I will verify:
- ✅ All 6 tests pass
- ✅ Backward compatibility maintained
- ✅ Recursive validation works (INV-0019)
- ✅ Clear validation reports per scope
- ✅ No breaking changes

---

## Prompt 4: Implement Multi-Scope CLI (COMP-0004)

### Context
You are creating a new Click-based CLI that provides scope-aware commands for ADR operations.

### Constraints (MUST enforce)

**CAP-0004**: CLI commands MUST work from any directory with consistent behavior

**INV-0014**: MUST support `--scope` parameter to override auto-detection

**INV-0019**: MUST support `--recursive` flag for multi-scope operations

### Component Specification (COMP-0004)

**File**: `src/adr_kit/cli/__init__.py`
```python
"""CLI module for ADR toolkit."""

from .main import cli

__all__ = ['cli']
```

**File**: `src/adr_kit/cli/main.py`

**CLI Structure**:
```python
import click
from pathlib import Path
from adr_kit.generators import ManifestGenerator
from adr_kit.validators import ADRValidator
from adr_kit.scope import ProjectScopeResolver

@click.group()
def cli():
    """ADR Architecture Kit - Multi-scope ADR management."""
    pass

@cli.command('generate-manifest')
@click.option('--scope', type=click.Path(exists=True), help='Project scope directory')
@click.option('--recursive', is_flag=True, help='Generate for all sub-modules')
@click.option('--output', type=click.Path(), help='Output file path')
def generate_manifest(scope, recursive, output):
    """Generate manifest.yaml for ADRs."""
    # Implementation...

@cli.command('validate')
@click.option('--scope', type=click.Path(exists=True), help='Project scope directory')
@click.option('--recursive', is_flag=True, help='Validate all sub-modules')
@click.option('--cross-references', is_flag=True, help='Validate cross-references')
def validate(scope, recursive, cross_references):
    """Validate ADRs in scope."""
    # Implementation...

@cli.command('scope')
@click.option('--recursive', is_flag=True, help='Show all sub-modules')
def show_scope(recursive):
    """Show detected project scope(s)."""
    # Implementation...
```

### Test Requirements

**File**: `tests/test_cli.py`

Required tests:
1. `test_cli_generate_manifest_auto_detect` - Works without --scope
2. `test_cli_generate_manifest_explicit_scope` - Works with --scope
3. `test_cli_generate_manifest_recursive` - --recursive flag works
4. `test_cli_validate_auto_detect` - Validation auto-detects
5. `test_cli_validate_recursive` - Recursive validation
6. `test_cli_scope_display` - Shows scope info
7. `test_cli_help_text` - Help is clear and complete

### Implementation Strategy (IMPL-0001: TDD)

**Red-Green-Refactor**:
1. **Red**: Test CLI invocation and help text
2. **Green**: Implement basic CLI structure
3. **Red**: Test `generate-manifest` command
4. **Green**: Implement manifest generation
5. **Red**: Test `validate` command
6. **Green**: Implement validation
7. **Red**: Test `scope` command
8. **Green**: Implement scope display
9. **Refactor**: Extract common logic, improve error messages

### Dependencies
```python
import click
from pathlib import Path
from adr_kit.generators import ManifestGenerator
from adr_kit.validators import ADRValidator
from adr_kit.scope import ProjectScopeResolver, ProjectScope
```

### Entry Point Configuration

**File**: `pyproject.toml` (add/modify)
```toml
[project.scripts]
adr = "adr_kit.cli.main:cli"

[project.optional-dependencies]
cli = ["click>=8.0"]
```

### Validation Criteria

I will verify:
- ✅ All 7 CLI tests pass
- ✅ Commands work from any directory (CAP-0004)
- ✅ `--scope` parameter works (INV-0014)
- ✅ `--recursive` flag works (INV-0019)
- ✅ Help text is clear and complete
- ✅ Error messages are user-friendly
- ✅ CLI entry point works: `adr --help`

---

## Implementation Order

Execute prompts in this order (dependencies):

1. **Prompt 1** (Scope Resolver) - Foundation, no dependencies
2. **Prompt 2** (Manifest Generator) - Depends on Scope Resolver
3. **Prompt 3** (ADR Validator) - Depends on Scope Resolver
4. **Prompt 4** (CLI) - Depends on all above

---

## Validation Process

After each prompt implementation, I will:

### 1. Code Review
- ✅ Check adherence to component specifications
- ✅ Verify invariant enforcement (INV-*)
- ✅ Confirm implementation decisions followed (IMPL-*)
- ✅ Review type hints and documentation

### 2. Test Verification
- ✅ Run governance bundle: `adr governance-checks`
- ✅ Verify all required tests exist
- ✅ Check test coverage for new code
- ✅ Validate test quality (clear, isolated, deterministic)

### 3. Integration Testing
- ✅ Test with real workspace (adr-architecture-kit)
- ✅ Test with sub-module (ste-runtime)
- ✅ Verify backward compatibility
- ✅ Test CLI from different directories

### 4. ADR Compliance Check
- ✅ All invariants enforced (INV-0014 through INV-0019)
- ✅ All capabilities delivered (CAP-0001 through CAP-0004)
- ✅ All components implemented (COMP-0001 through COMP-0004)
- ✅ All implementation decisions followed (IMPL-0001 through IMPL-0006)

### 5. Documentation Verification
- ✅ Docstrings present and accurate
- ✅ Type hints complete
- ✅ Help text clear (for CLI)
- ✅ Error messages user-friendly

---

## Success Criteria (from ADR-L-0002)

Implementation is complete when:

✅ **CAP-0001**: Automatic scope detection works from any directory  
✅ **CAP-0002**: Scoped manifest generation includes only scope's ADRs  
✅ **CAP-0003**: Scoped validation works, recursive mode validates all  
✅ **CAP-0004**: CLI commands work from any directory  

✅ **INV-0014**: Explicit `--scope` parameter works  
✅ **INV-0015**: Marker hierarchy matches specification exactly  
✅ **INV-0016**: Each scope maintains independent `adrs/` and `manifest.yaml`  
✅ **INV-0017**: Cross-scope references use qualified IDs (documentation)  
✅ **INV-0018**: Workspace boundary enforcement prevents escape  
✅ **INV-0019**: Recursive validation validates all sub-modules  

✅ **IMPL-0001**: TDD methodology followed (tests first)  
✅ **IMPL-0004**: Backward compatibility maintained  

✅ **All tests pass**: 40+ tests across 4 test files  
✅ **Real workspace works**: adr-architecture-kit + ste-runtime detected  

---

## Notes for CODEX

- **Follow TDD strictly**: Write tests first (Red), implement (Green), refactor
- **Maintain backward compatibility**: Existing code must work unchanged
- **Clear error messages**: Help users understand what went wrong
- **Type hints everywhere**: Full type coverage for IDE support
- **Docstrings required**: Document all public methods
- **Test isolation**: Each test should be independent
- **Real-world testing**: Test with actual adr-architecture-kit workspace

---

## Questions for Implementation

If you encounter ambiguity:

1. **Marker detection order unclear?** → Use INV-0015 hierarchy exactly
2. **Boundary enforcement unclear?** → Stop at `.git` or system dirs (INV-0018)
3. **Backward compatibility concern?** → Existing API unchanged (IMPL-0004)
4. **Test scenario unclear?** → Ask me before implementing
5. **Error handling unclear?** → Fail fast with clear message

---

**Ready for CODEX implementation!**

Each prompt is self-contained with:
- Clear constraints (invariants)
- Detailed specifications (components)
- Test requirements (validation)
- TDD guidance (methodology)
- Validation criteria (acceptance)
