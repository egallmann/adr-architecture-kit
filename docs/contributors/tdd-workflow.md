# Test-Driven Development Workflow for ADR Kit

**Authority**: ADR-L-0003 DEC-0033 (TDD methodology); scope-resolution embodiment ADR-PC-0008 IMPL-0022

## Why TDD for ADR Kit?

This is a **governance tool that validates architecture decisions**. It must be provably correct because:

1. **Validation errors halt development workflows** - false positives are costly
2. **Generated manifests feed AI reasoning** - incorrect data corrupts cognition
3. **Multi-scope affects multiple projects** - bugs propagate widely
4. **Schema validation is foundational** - must be deterministic and correct

### STE Alignment

TDD directly implements STE principles:

| STE Principle | TDD Implementation |
|---------------|-------------------|
| **SYS-2**: Deterministic Cognition | Tests enforce deterministic behavior |
| **SYS-4**: Drift Prevention | Tests detect implementation drift |
| **PRIME-1**: No Implicit Assumptions | Tests make behavior explicit |
| **INV-0001**: Schema Validation | Tests prove validation correctness |

## Red-Green-Refactor Cycle

### 🔴 RED: Write Failing Test

Write a test that **specifies the desired behavior**. The test should fail because the feature doesn't exist yet.

**Example**: Adding scope boundary validation

```python
# tests/test_scope_resolver.py

def test_scope_resolution_stops_at_workspace_boundary():
    """Test INV-0018: Scope resolution must not traverse above workspace root."""
    # Arrange
    resolver = ProjectScopeResolver()
    home_dir = Path.home()
    
    # Act & Assert
    with pytest.raises(ValueError, match="workspace boundary"):
        resolver.resolve(start_dir=home_dir / "random-dir")
```

**Run test** (should fail):
```bash
pytest tests/test_scope_resolver.py::test_scope_resolution_stops_at_workspace_boundary -v
# FAILED - feature not implemented yet
```

### 🟢 GREEN: Make Test Pass

Implement the **minimum code** needed to make the test pass. Don't worry about elegance yet.

```python
# src/adr_kit/scope/resolver.py

def _is_workspace_boundary(self, path: Path) -> bool:
    """Check if path is a workspace boundary (INV-0018)."""
    path_parts = path.parts
    
    # Stop at system directories
    for boundary in self.SYSTEM_BOUNDARIES:
        if boundary in path_parts:
            if path.name == boundary:
                return True
    
    return False

def _find_project_root(self, start_dir: Path) -> Optional[Path]:
    """Find project root by searching for markers."""
    current = start_dir
    
    while current != Path(current.anchor):
        # Check for workspace boundary (INV-0018)
        if self._is_workspace_boundary(current):
            return None  # Stop here
        
        # ... rest of marker detection logic
```

**Run test** (should pass):
```bash
pytest tests/test_scope_resolver.py::test_scope_resolution_stops_at_workspace_boundary -v
# PASSED ✓
```

### 🔵 REFACTOR: Improve Design

Now that the test passes, **improve the code quality** while keeping tests green.

```python
# Refactor: Extract boundary checking logic

class WorkspaceBoundaryEnforcer:
    """Enforces workspace boundaries per INV-0018."""
    
    SYSTEM_BOUNDARIES = ['Users', 'home', 'Documents']
    
    def is_boundary(self, path: Path) -> bool:
        """Check if path is at a system boundary."""
        return path.name in self.SYSTEM_BOUNDARIES

# Use in resolver
def _find_project_root(self, start_dir: Path) -> Optional[Path]:
    boundary_enforcer = WorkspaceBoundaryEnforcer()
    
    while current != Path(current.anchor):
        if boundary_enforcer.is_boundary(current):
            return None
        # ...
```

**Run tests again** (should still pass):
```bash
pytest tests/test_scope_resolver.py -v
# All tests PASSED ✓
```

## TDD Workflow for New Features

### Step 1: Understand the Requirement

From ADR or user story, identify:
- **What** behavior is needed
- **Which invariant** it implements
- **What** edge cases exist
- **What** error conditions to handle

**Example**: Implement recursive scope discovery (CAP-0001)

### Step 2: Write Test Cases

Start with the **simplest case**, then add complexity:

```python
# Test 1: Simple case (one sub-module)
def test_find_single_sub_module():
    """Test recursive discovery finds one sub-module."""
    # Setup: workspace with one sub-module
    # Assert: finds both workspace and sub-module

# Test 2: Multiple sub-modules
def test_find_multiple_sub_modules():
    """Test recursive discovery finds all sub-modules."""
    # Setup: workspace with multiple sub-modules
    # Assert: finds all scopes

# Test 3: Edge case (no sub-modules)
def test_recursive_with_no_sub_modules():
    """Test recursive discovery with no sub-modules."""
    # Setup: workspace with no sub-modules
    # Assert: finds only workspace

# Test 4: Edge case (max depth)
def test_recursive_respects_max_depth():
    """Test recursive search stops at max depth."""
    # Setup: deeply nested sub-modules
    # Assert: only finds within depth limit
```

### Step 3: Run Tests (All Should Fail)

```bash
pytest tests/test_scope_resolver.py::TestRecursiveScopeDiscovery -v
# 4 FAILED - feature not implemented
```

### Step 4: Implement Feature

Implement **one test at a time**:

```python
# Make test_find_single_sub_module pass
def resolve_recursive(self, start_dir: Optional[Path] = None) -> List[ProjectScope]:
    scopes = []
    root_scope = self.resolve(start_dir)
    scopes.append(root_scope)
    
    # Simple implementation for first test
    for subdir in root_scope.root.iterdir():
        if subdir.is_dir() and (subdir / "package.json").exists():
            sub_scope = self.resolve(subdir)
            scopes.append(sub_scope)
    
    return scopes
```

**Run first test**:
```bash
pytest tests/test_scope_resolver.py::test_find_single_sub_module -v
# PASSED ✓
```

**Run second test** (will fail - doesn't handle multiple markers):
```bash
pytest tests/test_scope_resolver.py::test_find_multiple_sub_modules -v
# FAILED - only finds package.json, not pyproject.toml
```

**Improve implementation**:
```python
def resolve_recursive(self, start_dir: Optional[Path] = None) -> List[ProjectScope]:
    scopes = []
    root_scope = self.resolve(start_dir)
    scopes.append(root_scope)
    
    # Enhanced: check all markers
    sub_scopes = self._find_sub_modules(root_scope.root)
    scopes.extend(sub_scopes)
    
    return scopes

def _find_sub_modules(self, root: Path) -> List[ProjectScope]:
    # Implementation that checks all markers
    # ...
```

Continue until **all tests pass**.

### Step 5: Refactor

Improve code quality while keeping tests green:
- Extract helper methods
- Improve naming
- Reduce duplication
- Optimize performance

**Run tests after each refactor**:
```bash
pytest tests/test_scope_resolver.py -v
# All PASSED ✓
```

## TDD for Different Component Types

### Validators (Critical - Must Be Correct)

**High test coverage required** (INV-0021):

```python
# 1. Write tests for valid input
def test_validate_valid_logical_adr():
    validator = ADRValidator()
    result = validator.validate_file("adrs/logical/ADR-L-0001.yaml")
    assert result.valid is True

# 2. Write tests for invalid input  
def test_validate_missing_required_field():
    validator = ADRValidator()
    result = validator.validate_file("test-data/invalid-missing-title.yaml")
    assert result.valid is False
    assert any("title" in e.message for e in result.errors)

# 3. Write tests for edge cases
def test_validate_empty_decisions_list():
    # Should warn, not error
    pass

# 4. Implement validation logic
# 5. Refactor
```

### Generators (Complex Logic)

**Test-first for correctness**:

```python
# 1. Test expected output structure
def test_generate_manifest_includes_all_adrs():
    generator = ManifestGenerator()
    manifest = generator.generate_from_directory("adrs")
    
    # Verify structure
    assert manifest.schema_version == "1.0"
    assert len(manifest.adrs) >= 2
    assert "by_domain" in manifest.__dict__

# 2. Test aggregation logic
def test_manifest_statistics_computed_correctly():
    generator = ManifestGenerator()
    manifest = generator.generate_from_directory("adrs")
    
    assert manifest.statistics.total_adrs == (
        manifest.statistics.logical_adrs + 
        manifest.statistics.physical_adrs
    )

# 3. Implement generation logic
# 4. Refactor
```

### Scope Resolution (Security-Critical)

**Test boundaries thoroughly** (INV-0018):

```python
# Security tests FIRST
def test_cannot_traverse_above_workspace():
    """SECURITY: Prevent scanning home directory."""
    pass

def test_cannot_traverse_to_system_directories():
    """SECURITY: Prevent scanning C:\Windows, /etc, etc."""
    pass

def test_explicit_scope_validated():
    """SECURITY: Validate explicit scope is within bounds."""
    pass

# Then implement with security in mind
```

## TDD Best Practices for ADR Kit

### 1. Test Names Are Specifications

```python
# ❌ Bad: Vague test name
def test_validator():
    pass

# ✅ Good: Specification as test name
def test_logical_adr_without_decisions_generates_warning():
    """Test that logical ADRs should have at least one decision (completeness check)."""
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_scope_detection_from_subdirectory():
    # Arrange: Set up test conditions
    workspace = create_test_workspace()
    subdir = workspace / "src" / "module"
    
    # Act: Execute the behavior
    resolver = ProjectScopeResolver()
    scope = resolver.resolve(start_dir=subdir)
    
    # Assert: Verify expectations
    assert scope.root == workspace
    assert scope.marker == "PROJECT.yaml"
```

### 3. Test One Thing at a Time

```python
# ❌ Bad: Tests multiple behaviors
def test_scope_resolver():
    # Tests detection AND validation AND metadata extraction
    pass

# ✅ Good: Focused tests
def test_scope_detection_via_project_yaml():
    # Only tests detection mechanism
    pass

def test_scope_metadata_extraction():
    # Only tests metadata extraction
    pass
```

### 4. Use Fixtures for Setup

```python
@pytest.fixture
def test_workspace(tmp_path):
    """Create test workspace with ADRs."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "PROJECT.yaml").write_text("project:\n  name: test")
    (workspace / "adrs" / "logical").mkdir(parents=True)
    return workspace

def test_with_fixture(test_workspace):
    resolver = ProjectScopeResolver()
    scope = resolver.resolve(start_dir=test_workspace)
    assert scope.root == test_workspace
```

### 5. Test Real Workspace (Dogfooding)

```python
def test_validate_actual_workspace_adrs():
    """Test validator works on actual workspace ADRs (dogfooding)."""
    workspace_root = Path(__file__).parent.parent
    validator = ADRValidator()
    
    results = validator.validate_directory(workspace_root / "adrs")
    
    # Our own ADRs should be valid!
    assert all(r.valid for r in results.values())
```

## TDD for Multi-Scope Features

### Example: Implementing Recursive Validation

#### Step 1: Write Tests (Red)

```python
# tests/test_adr_validator.py

class TestRecursiveValidation:
    """Test INV-0019: Recursive validation of all scopes."""
    
    def test_validate_recursive_finds_all_scopes(self):
        """Test that recursive validation finds workspace + sub-modules."""
        validator = ADRValidator()
        
        all_results = validator.validate_recursive()
        
        # Should find at least workspace
        assert len(all_results) >= 1
        assert "adr-architecture-kit" in all_results
        
        # Should find ste-runtime if it exists
        if (Path.cwd() / "ste-runtime").exists():
            assert "ste-runtime" in all_results
    
    def test_validate_recursive_validates_each_scope_independently(self):
        """Test that each scope is validated independently."""
        validator = ADRValidator()
        
        all_results = validator.validate_recursive()
        
        # Each scope should have its own validation results
        for scope_name, results in all_results.items():
            assert isinstance(results, dict)
            # Results should be for that scope only
            assert all(scope_name in str(path) or "adrs" in str(path) 
                      for path in results.keys())
    
    def test_validate_recursive_reports_errors_per_scope(self):
        """Test that errors are reported per scope."""
        # This test would use fixtures with intentional errors
        pass
```

**Run tests** (should fail):
```bash
pytest tests/test_adr_validator.py::TestRecursiveValidation -v
# FAILED - validate_recursive method doesn't exist
```

#### Step 2: Implement (Green)

```python
# src/adr_kit/validators/adr_validator.py

def validate_recursive(self, scope: Optional[ProjectScope] = None) -> Dict[str, dict]:
    """Validate ADRs for all scopes recursively (ADR-L-0002: INV-0019)."""
    if scope is None:
        scope = self.scope_resolver.resolve()
    
    scopes = self.scope_resolver.resolve_recursive(scope.root)
    all_results = {}
    
    for s in scopes:
        if s.adr_dir.exists():
            try:
                results = self.validate_directory(s.adr_dir, s)
                all_results[s.name or str(s.root)] = results
            except Exception as e:
                print(f"Warning: Failed to validate {s.name}: {e}")
    
    return all_results
```

**Run tests** (should pass):
```bash
pytest tests/test_adr_validator.py::TestRecursiveValidation -v
# PASSED ✓
```

#### Step 3: Refactor (Blue)

Improve the implementation:

```python
# Refactor: Extract error handling

def validate_recursive(self, scope: Optional[ProjectScope] = None) -> Dict[str, dict]:
    """Validate ADRs for all scopes recursively."""
    scope = scope or self.scope_resolver.resolve()
    scopes = self.scope_resolver.resolve_recursive(scope.root)
    
    return {
        s.name or str(s.root): self._validate_scope_safe(s)
        for s in scopes
        if s.adr_dir.exists()
    }

def _validate_scope_safe(self, scope: ProjectScope) -> dict:
    """Validate scope with error handling."""
    try:
        return self.validate_directory(scope.adr_dir, scope)
    except Exception as e:
        print(f"Warning: Failed to validate {scope.name}: {e}")
        return {}
```

**Run tests** (should still pass):
```bash
pytest tests/test_adr_validator.py::TestRecursiveValidation -v
# PASSED ✓
```

## TDD Workflow Commands

### Quick Feedback Loop

```bash
# Watch mode - tests run on file save
pytest tests/ --watch

# Or use pytest-watch
ptw tests/ -- -v
```

### Test-First Development Session

```bash
# 1. Write failing test
vim tests/test_scope_resolver.py

# 2. Run test (RED)
pytest tests/test_scope_resolver.py::test_new_feature -v
# FAILED ✓ (expected)

# 3. Implement feature
vim src/adr_kit/scope/resolver.py

# 4. Run test (GREEN)
pytest tests/test_scope_resolver.py::test_new_feature -v
# PASSED ✓

# 5. Refactor
vim src/adr_kit/scope/resolver.py

# 6. Run all tests (ensure no regressions)
pytest tests/test_scope_resolver.py -v
# All PASSED ✓
```

### Coverage-Driven Development

```bash
# Run with coverage to find untested code
pytest tests/ --cov=src/adr_kit --cov-report=term-missing

# Shows which lines aren't covered
# Write tests for uncovered lines
# Repeat until coverage target met
```

## TDD for Different Scenarios

### New Component

```python
# 1. Define interface via test
def test_new_component_api():
    component = NewComponent()
    result = component.do_something(input)
    assert result == expected

# 2. Implement interface
class NewComponent:
    def do_something(self, input):
        return expected

# 3. Add edge cases
def test_new_component_handles_none():
    component = NewComponent()
    result = component.do_something(None)
    assert result is None  # or raises ValueError

# 4. Implement error handling
```

### Bug Fix

```python
# 1. Write test that reproduces bug
def test_bug_456_scope_detection_fails_on_windows_paths():
    """Regression test for issue #456."""
    windows_path = Path("C:/Users/Erik/Projects/test")
    resolver = ProjectScopeResolver()
    
    # This should work but currently fails
    scope = resolver.resolve(start_dir=windows_path)
    assert scope is not None

# 2. Fix bug
# 3. Test passes
# 4. Bug can never return (test prevents it)
```

### Refactoring

```python
# 1. Ensure comprehensive test coverage FIRST
pytest tests/test_scope_resolver.py --cov=src/adr_kit/scope/resolver.py
# Coverage: 95%

# 2. Refactor with confidence
# 3. Run tests continuously
# 4. Tests prove behavior unchanged
```

## Integration with Development Tools

### VS Code / Cursor

```json
// .vscode/settings.json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "python.testing.autoTestDiscoverOnSaveEnabled": true
}
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest tests/ -v
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: TDD Validation

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest tests/ -v --cov=src/adr_kit --cov-fail-under=80
```

## TDD Metrics

### Measure TDD Adoption

```bash
# Test-to-code ratio
cloc tests/ src/adr_kit/
# Target: ~1:1 ratio (similar lines of test and production code)

# Coverage
pytest tests/ --cov=src/adr_kit --cov-report=term
# Target: 80%+ for critical components

# Test execution time
pytest tests/ --durations=10
# Target: < 30 seconds total (INV-0023)
```

## When NOT to Use TDD

TDD is not always optimal:

### Skip TDD for:
- **Exploratory coding**: Spike solutions, prototypes
- **Trivial code**: Simple getters/setters, data classes
- **UI/UX iteration**: Visual design requires experimentation
- **Performance optimization**: Profile-guided optimization

### Use TDD for:
- ✅ **Validators**: Must be provably correct
- ✅ **Generators**: Complex logic, many edge cases
- ✅ **Scope resolution**: Security-critical
- ✅ **CLI commands**: User-facing behavior
- ✅ **Bug fixes**: Prevent regression

## Practical Tips

### 1. Start with the Simplest Test

```python
# Start here (simplest case)
def test_scope_resolver_works():
    resolver = ProjectScopeResolver()
    scope = resolver.resolve()
    assert scope is not None

# Not here (complex case)
def test_scope_resolver_handles_nested_submodules_with_conflicting_markers():
    # Too complex for first test
```

### 2. One Assert Per Test (When Possible)

```python
# ✅ Good: Clear failure message
def test_scope_has_root():
    scope = resolver.resolve()
    assert scope.root is not None

def test_scope_has_adr_dir():
    scope = resolver.resolve()
    assert scope.adr_dir is not None

# ❌ Less clear: Which assertion failed?
def test_scope_has_all_fields():
    scope = resolver.resolve()
    assert scope.root is not None
    assert scope.adr_dir is not None
    assert scope.manifest_path is not None
```

### 3. Test Error Messages

```python
def test_no_project_found_has_helpful_error():
    """Test that error messages guide users to solution."""
    resolver = ProjectScopeResolver()
    
    with pytest.raises(ValueError) as exc_info:
        resolver.resolve(start_dir=Path("/empty"))
    
    # Error should mention what markers were searched
    assert "PROJECT.yaml" in str(exc_info.value)
    assert "package.json" in str(exc_info.value)
```

### 4. Use Real Data When Possible

```python
def test_validate_actual_workspace_adrs():
    """Dogfooding: Validate our own ADRs."""
    workspace = Path(__file__).parent.parent
    validator = ADRValidator()
    
    results = validator.validate_directory(workspace / "adrs")
    
    # Our ADRs should be valid!
    for path, result in results.items():
        assert result.valid, f"{path} is invalid: {result.errors}"
```

## Summary

**TDD for ADR Kit**:
- ✅ **Architecturally aligned** with STE principles
- ✅ **Necessary** for governance tool correctness
- ✅ **Documented** in ADR-L-0003 DEC-0005
- ✅ **Implemented** in ADR-P-0003 IMPL-0001
- ✅ **Practical** with clear workflow and examples

**Benefits**:
- Provable correctness for validation logic
- Immediate feedback on implementation
- Safe refactoring with test safety net
- Living documentation via test examples
- Reduced debugging time
- Higher confidence in multi-scope complexity

**Trade-offs**:
- Slower initial development (faster overall with fewer bugs)
- Requires discipline (write test first, not after)
- Learning curve for TDD newcomers

For a system that **validates architecture decisions and generates machine-readable state**, TDD is not optional - it's **architectural alignment**.
